"""
Tests para bot.services.groq

Testa o GroqService com mocks para nao chamar a API real.
"""

from unittest.mock import MagicMock, patch

import pytest
from bot.config import Config
from bot.services.groq import GroqService


class MockConfig:
    """Config mockada para testes."""
    groq_api_key = "test_key_123"
    groq_model = "test-model"


class TestGroqService:
    """Testes para GroqService."""

    def test_initialization(self):
        """GroqService e inicializado corretamente."""
        config = MockConfig()
        service = GroqService(config)

        assert service.api_key == "test_key_123"
        assert service.model == "test-model"
        assert service.max_retries == 2
        assert service.retry_delay == 2
        assert service._client is None

    def test_get_client_lazy(self):
        """Cliente Groq e criado sob demanda (lazy)."""
        config = MockConfig()
        service = GroqService(config)

        assert service._client is None  # Ainda nao criado

        client = service._get_client()
        assert client is not None
        assert service._client is not None  # Cacheado

    @patch("bot.services.groq.GroqClient")
    def test_generate_reply_empty_history(self, mock_groq_client):
        """generate_reply com historico vazio usa user_message direto."""
        # Configura o mock
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        mock_choice = MagicMock()
        mock_choice.message.content = "Hello student! How can I help you?"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_instance.chat.completions.create.return_value = mock_response

        config = MockConfig()
        service = GroqService(config)

        # Testa com historico vazio
        import asyncio
        result = asyncio.run(service.generate_reply("", "Hello!"))

        assert result == "Hello student! How can I help you?"

        # Verifica se chamou a API com os parametros corretos
        call_args = mock_instance.chat.completions.create.call_args
        assert call_args is not None
        kwargs = call_args[1]
        assert kwargs["model"] == "test-model"
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 400
        # Deve ter system prompt + user_message
        assert len(kwargs["messages"]) == 2
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"
        assert kwargs["messages"][1]["content"] == "Hello!"

    @patch("bot.services.groq.GroqClient")
    def test_generate_reply_with_history(self, mock_groq_client):
        """generate_reply com historico existente."""
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        mock_choice = MagicMock()
        mock_choice.message.content = "Great question!"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_instance.chat.completions.create.return_value = mock_response

        config = MockConfig()
        service = GroqService(config)

        history = "Student: Hello!\nTeacher: Hi! How are you?\nStudent: I'm fine!"
        import asyncio
        result = asyncio.run(service.generate_reply(history, "I'm fine!"))

        assert result == "Great question!"

        # Verifica mensagens: system + historico + user_message
        call_args = mock_instance.chat.completions.create.call_args
        kwargs = call_args[1]
        messages = kwargs["messages"]
        assert len(messages) == 5  # system + 3 historico + user_message
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi! How are you?"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "I'm fine!"
        # user_message SEMPRE e adicionado no final
        assert messages[4]["role"] == "user"
        assert messages[4]["content"] == "I'm fine!"

    @patch("bot.services.groq.GroqClient")
    def test_generate_reply_empty_response(self, mock_groq_client):
        """Resposta vazia da API retorna None."""
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_instance.chat.completions.create.return_value = mock_response

        config = MockConfig()
        service = GroqService(config)

        import asyncio
        result = asyncio.run(service.generate_reply("", "Hello"))
        assert result is None

    @patch("bot.services.groq.GroqClient")
    def test_generate_reply_no_choices(self, mock_groq_client):
        """Resposta sem choices retorna None."""
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.choices = []
        mock_instance.chat.completions.create.return_value = mock_response

        config = MockConfig()
        service = GroqService(config)

        import asyncio
        result = asyncio.run(service.generate_reply("", "Hello"))
        assert result is None

    @patch("bot.services.groq.GroqClient")
    def test_retry_on_error(self, mock_groq_client):
        """Retry e feito apos falha."""
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        # Falha 2x, sucesso na 3a
        mock_instance.chat.completions.create.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            MagicMock(
                choices=[MagicMock(message=MagicMock(content="Success!"))]
            ),
        ]

        config = MockConfig()
        service = GroqService(config)
        service.retry_delay = 0  # Sem delay para teste rapido

        import asyncio
        result = asyncio.run(service.generate_reply("", "Hello"))
        assert result == "Success!"
        assert mock_instance.chat.completions.create.call_count == 3

    @patch("bot.services.groq.GroqClient")
    def test_all_retries_fail(self, mock_groq_client):
        """Apos 3 tentativas falharem, retorna None."""
        mock_instance = MagicMock()
        mock_groq_client.return_value = mock_instance

        mock_instance.chat.completions.create.side_effect = Exception("Always fails")

        config = MockConfig()
        service = GroqService(config)
        service.retry_delay = 0

        import asyncio
        result = asyncio.run(service.generate_reply("", "Hello"))
        assert result is None
        assert mock_instance.chat.completions.create.call_count == 3

    @patch("bot.services.groq.GroqClient")
    def test_build_messages_includes_system_prompt(self, mock_groq_client):
        """_build_messages sempre inclui o system prompt."""
        config = MockConfig()
        service = GroqService(config)

        messages = service._build_messages("", "Hello")
        assert messages[0]["role"] == "system"
        assert "English teacher" in messages[0]["content"]

    @patch("bot.services.groq.GroqClient")
    def test_build_messages_with_history(self, mock_groq_client):
        """_build_messages converte historico corretamente."""
        config = MockConfig()
        service = GroqService(config)

        history = "Teacher: Hello!\nStudent: Hi!"
        messages = service._build_messages(history, "How are you?")

        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Hi!"
        # user_message sempre adicionado
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "How are you?"
