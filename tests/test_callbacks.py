"""
Tests para bot.handlers.callbacks

Testa os callbacks dos botoes inline com mocks do Telegram.
Navegacao: menu, how_it_works, start_conversation, show_vocab, show_topics
Acao: more_examples, explain_word, practice_this
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.callbacks import handle_callback
from bot.utils.keyboards import SPEED_OPTIONS, DEFAULT_SPEED_BY_LEVEL


class TestSpeedCallbacks:
    """Testes para callbacks de velocidade do TTS."""

    @pytest.mark.asyncio
    async def test_set_speed_0_85(self, mock_update, configured_context):
        """set_speed_0.85 salva 0.85 em user_data e mostra confirmacao."""
        mock_update.callback_query.data = "set_speed_0.85"
        configured_context.user_data = {}

        await handle_callback(mock_update, configured_context)

        assert configured_context.user_data.get("tts_speed") == 0.85
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Speed set to 0.85x" in text

    @pytest.mark.asyncio
    async def test_set_speed_1_25(self, mock_update, configured_context):
        """set_speed_1.25 salva 1.25 em user_data."""
        mock_update.callback_query.data = "set_speed_1.25"
        configured_context.user_data = {}

        await handle_callback(mock_update, configured_context)

        assert configured_context.user_data.get("tts_speed") == 1.25
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Speed set to 1.25x" in text

    @pytest.mark.asyncio
    async def test_set_speed_1_0_default(self, mock_update, configured_context):
        """set_speed_1.0 salva 1.0 em user_data."""
        mock_update.callback_query.data = "set_speed_1.0"
        configured_context.user_data = {}

        await handle_callback(mock_update, configured_context)

        assert configured_context.user_data.get("tts_speed") == 1.0
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Speed set to 1.0x" in text

    def test_all_speed_options_valid(self):
        """Todos os valores em SPEED_OPTIONS estao dentro do range esperado."""
        assert all(0.75 <= s <= 1.25 for s in SPEED_OPTIONS)
        assert len(SPEED_OPTIONS) == 5

    def test_default_speed_by_level(self):
        """Velocidades padrao estao corretas para cada nivel."""
        assert DEFAULT_SPEED_BY_LEVEL["A1"] == 0.85
        assert DEFAULT_SPEED_BY_LEVEL["A2"] == 0.9
        assert DEFAULT_SPEED_BY_LEVEL["B1"] == 1.0


class TestCallbackNavigation:
    """Testes para botoes de navegacao."""

    @pytest.mark.asyncio
    async def test_back_to_menu(self, mock_update, configured_context):
        """back_to_menu volta ao menu principal."""
        mock_update.callback_query.data = "back_to_menu"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Hello" in text
        assert "LinguaBot" in text

    @pytest.mark.asyncio
    async def test_how_it_works(self, mock_update, configured_context):
        """how_it_works mostra explicacao."""
        mock_update.callback_query.data = "how_it_works"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "How LinguaBot Works" in text
        assert "tips" in text.lower()

    @pytest.mark.asyncio
    async def test_start_conversation(self, mock_update, configured_context):
        """start_conversation mostra sugestao de topico."""
        mock_update.callback_query.data = "start_conversation"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "let's start" in text.lower() or "Let's practice" in text

    @pytest.mark.asyncio
    async def test_start_topic_greetings(self, mock_update, configured_context):
        """start_topic_Greetings inicia conversa sobre Greetings."""
        mock_update.callback_query.data = "start_topic_Greetings"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Greetings" in text or "talk" in text.lower()

    @pytest.mark.asyncio
    async def test_unknown_callback(self, mock_update, configured_context):
        """Callback desconhecido mostra mensagem de erro."""
        mock_update.callback_query.data = "some_random_data"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "didn't understand" in text.lower()


class TestCallbackActions:
    """Testes para botoes de acao (Example, Explain, Practice)."""

    @pytest.mark.asyncio
    async def test_more_examples_no_history(self, mock_update, configured_context):
        """more_examples sem historico mostra aviso via nova mensagem."""
        mock_update.callback_query.data = "more_examples"
        await handle_callback(mock_update, configured_context)

        # Agora usa reply_text (nova mensagem) em vez de edit_message_text
        mock_update.callback_query.message.reply_text.assert_called()
        calls = mock_update.callback_query.message.reply_text.call_args_list
        last_text = calls[-1][0][0]
        assert "start a conversation" in last_text.lower()

    @pytest.mark.asyncio
    async def test_more_examples_with_history(self, mock_update, configured_context):
        """more_examples com historico chama Groq e envia nova mensagem."""
        conv = configured_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello!")
        conv.add_assistant_message("Hi! How are you?")

        mock_update.callback_query.data = "more_examples"
        await handle_callback(mock_update, configured_context)

        configured_context.bot_data["groq"].generate_reply.assert_called_once()

        # A mensagem de carregamento foi enviada como nova mensagem
        mock_update.callback_query.message.reply_text.assert_called()
        calls = mock_update.callback_query.message.reply_text.call_args_list
        first_text = calls[0][0][0]
        assert "Generating more examples" in first_text

    @pytest.mark.asyncio
    async def test_explain_word_with_history(self, mock_update, configured_context):
        """explain_word com historico chama Groq e envia nova mensagem."""
        conv = configured_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("What is 'breakfast'?")
        conv.add_assistant_message("Breakfast is the first meal of the day!")

        mock_update.callback_query.data = "explain_word"
        await handle_callback(mock_update, configured_context)

        configured_context.bot_data["groq"].generate_reply.assert_called_once()

        mock_update.callback_query.message.reply_text.assert_called()
        calls = mock_update.callback_query.message.reply_text.call_args_list
        first_text = calls[0][0][0]
        assert "Looking up word" in first_text

    @pytest.mark.asyncio
    async def test_practice_this_with_history(self, mock_update, configured_context):
        """practice_this com historico chama Groq e envia nova mensagem."""
        conv = configured_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("I like dogs")
        conv.add_assistant_message("Great! Dogs are wonderful animals!")

        mock_update.callback_query.data = "practice_this"
        await handle_callback(mock_update, configured_context)

        configured_context.bot_data["groq"].generate_reply.assert_called_once()

        mock_update.callback_query.message.reply_text.assert_called()
        calls = mock_update.callback_query.message.reply_text.call_args_list
        first_text = calls[0][0][0]
        assert "Creating a practice" in first_text

    @pytest.mark.asyncio
    async def test_show_vocab(self, mock_update, configured_context, sample_vocab_entries):
        """show_vocab exibe vocabulario."""
        configured_context.bot_data["db"].get_vocab_count = AsyncMock(return_value=3)
        configured_context.bot_data["db"].get_vocab = AsyncMock(return_value=sample_vocab_entries)

        mock_update.callback_query.data = "show_vocab"
        await handle_callback(mock_update, configured_context)

        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "breakfast" in text
        assert "Vocabulary" in text
