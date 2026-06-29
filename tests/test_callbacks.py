"""
Tests para bot.handlers.callbacks

Testa os callbacks dos botoes inline com mocks do Telegram.
Navegacao: menu, how_it_works, start_conversation, show_vocab, show_topics
Acao: more_examples, explain_word, practice_this
"""

from __future__ import annotations

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


class TestConfigCallbacks:
    """Testes para callbacks do menu de configuracao."""

    @pytest.mark.asyncio
    async def test_show_config(self, mock_update, configured_context):
        """show_config exibe menu de configuracao."""
        configured_context.user_data = {}
        mock_update.callback_query.data = "show_config"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()
        assert configured_context.user_data.get("screen_type") == "config_menu"

    @pytest.mark.asyncio
    async def test_show_voice_picker(self, mock_update, configured_context):
        """show_voice_picker exibe seletor de voz."""
        mock_update.callback_query.data = "show_voice_picker"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()
        assert configured_context.user_data.get("screen_type") == "voice_picker"

    @pytest.mark.asyncio
    async def test_show_speed_picker(self, mock_update, configured_context):
        """show_speed_picker exibe seletor de velocidade."""
        mock_update.callback_query.data = "show_speed_picker"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()
        assert configured_context.user_data.get("screen_type") == "speed_picker"

    @pytest.mark.asyncio
    async def test_show_level_picker(self, mock_update, configured_context):
        """show_level_picker exibe seletor de nivel."""
        from bot.services.level_manager import LevelManager
        configured_context.bot_data["level_manager"] = LevelManager()
        configured_context.user_data = {}
        mock_update.callback_query.data = "show_level_picker"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()
        assert configured_context.user_data.get("screen_type") == "level_picker"


class TestVoiceCallbacks:
    """Testes para callbacks de selecao de voz."""

    @pytest.mark.asyncio
    async def test_set_voice_valid(self, mock_update, configured_context):
        """set_voice_com voz valida atualiza preferencia."""
        from bot.services.deepgram_tts import VOICE_IDS, VOICE_MAP
        configured_context.bot_data["deepgram_tts"] = MagicMock()
        valid_voice = VOICE_IDS[0]
        mock_update.callback_query.data = f"set_voice_{valid_voice}"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        assert configured_context.user_data.get("voice_id") == valid_voice

    @pytest.mark.asyncio
    async def test_set_voice_invalid(self, mock_update, configured_context):
        """set_voice_com voz invalida mostra erro."""
        configured_context.bot_data["deepgram_tts"] = MagicMock()
        mock_update.callback_query.data = "set_voice_invalid_voice"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Invalid voice" in text

    @pytest.mark.asyncio
    async def test_set_voice_without_tts_service(self, mock_update, mock_context):
        """set_voice_sem servico de audio mostra erro."""
        mock_update.callback_query.data = "set_voice_aura-2-thalia-en"
        await handle_callback(mock_update, mock_context)
        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "audio" in text.lower()


class TestLevelCallbacks:
    """Testes para callbacks de selecao de nivel."""

    @pytest.mark.asyncio
    async def test_set_level_valid(self, mock_update, configured_context):
        """set_level_com nivel valido atualiza e persiste."""
        from bot.services.level_manager import LevelManager
        level_mgr = LevelManager(default_level="A1")
        configured_context.bot_data["level_manager"] = level_mgr
        mock_update.callback_query.data = "set_level_B1"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        assert level_mgr.get_level(12345) == "B1"
        mock_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_level_without_manager(self, mock_update, configured_context):
        """set_level_sem level_manager mostra erro."""
        configured_context.bot_data["level_manager"] = None
        mock_update.callback_query.data = "set_level_A2"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_text.assert_called()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "not ready" in text.lower()

    @pytest.mark.asyncio
    async def test_set_level_updates_speed(self, mock_update, configured_context):
        """set_level_reseta velocidade para o padrao do nivel."""
        from bot.services.level_manager import LevelManager
        from bot.constants import DEFAULT_SPEED_BY_LEVEL
        level_mgr = LevelManager(default_level="A1")
        configured_context.bot_data["level_manager"] = level_mgr
        mock_update.callback_query.data = "set_level_A1"
        configured_context.user_data = {"tts_speed": 1.25}
        await handle_callback(mock_update, configured_context)
        assert configured_context.user_data.get("tts_speed") == DEFAULT_SPEED_BY_LEVEL["A1"]


class TestExpandCollapseCallbacks:
    """Testes para botoes de expandir/recolher."""

    @pytest.mark.asyncio
    async def test_show_more_options(self, mock_update, configured_context):
        """show_more_options expande botoes."""
        mock_update.callback_query.data = "show_more_options"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_hide_options(self, mock_update, configured_context):
        """hide_options recolhe botoes."""
        mock_update.callback_query.data = "hide_options"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_more_options_config_menu_ignored(self, mock_update, configured_context):
        """show_more_options em config_menu nao faz nada."""
        configured_context.user_data["screen_type"] = "config_menu"
        mock_update.callback_query.data = "show_more_options"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_more_options_in_voice_picker(self, mock_update, configured_context):
        """show_more_options em voice_picker nao faz nada."""
        configured_context.user_data["screen_type"] = "voice_picker"
        mock_update.callback_query.data = "show_more_options"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_reply_markup.assert_not_called()


class TestVocabPaginationCallbacks:
    """Testes para paginacao de vocabulario."""

    @pytest.mark.asyncio
    async def test_vocab_page_navigation(self, mock_update, configured_context, sample_vocab_entries):
        """vocab_page_N navega para pagina N."""
        configured_context.bot_data["db"].get_vocab_count = AsyncMock(return_value=3)
        configured_context.bot_data["db"].get_vocab = AsyncMock(return_value=sample_vocab_entries)
        mock_update.callback_query.data = "vocab_page_1"
        configured_context.user_data = {}
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_text.assert_called_once()
        assert configured_context.user_data.get("page") == 1
        assert configured_context.user_data.get("screen_type") == "vocab"

    @pytest.mark.asyncio
    async def test_vocab_page_no_db(self, mock_update, configured_context):
        """vocab_page_sem db mostra erro."""
        configured_context.bot_data["db"] = None
        mock_update.callback_query.data = "vocab_page_1"
        await handle_callback(mock_update, configured_context)
        mock_update.callback_query.edit_message_text.assert_called_once()
        text = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "not ready" in text.lower()
