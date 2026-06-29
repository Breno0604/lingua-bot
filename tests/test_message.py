"""
LinguaBot --- Tests for bot.handlers.message

Tests the text message handling flow:
  1. Guard clauses (no services, empty text, commands)
  2. Normal message flow with Groq response
  3. Vocabulary extraction and saving
  4. Audio generation with TTS orchestrator
  5. Rate limiter warnings
  6. Fallback when no audio is generated
  7. Button cleanup
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.handlers.message import handle_message
from bot.constants import DEFAULT_SPEED_BY_LEVEL
from bot.services.deepgram_tts import DEFAULT_VOICE_ID as DG_DEFAULT_VOICE_ID


# ──────────────────────────────────────────────
# Fixtures especificas para testes de message
# ──────────────────────────────────────────────

@pytest.fixture
def mock_level_manager():
    """Mock do LevelManager."""
    lm = MagicMock()
    lm.get_level = MagicMock(return_value="A1")
    return lm


@pytest.fixture
def message_update(mock_update):
    """Update do Telegram com reply_voice async."""
    mock_update.message.reply_voice = AsyncMock()
    voice_msg = MagicMock()
    voice_msg.message_id = 101
    mock_update.message.reply_voice.return_value = voice_msg
    return mock_update


@pytest.fixture
def configured_message_context(
    configured_context,
    mock_tts_orchestrator,
    mock_level_manager,
):
    """Context pre-configurado com servicos de mensagem."""
    configured_context.bot_data["tts_orchestrator"] = mock_tts_orchestrator
    configured_context.bot_data["level_manager"] = mock_level_manager
    configured_context.user_data = {}
    configured_context.bot.edit_message_reply_markup = AsyncMock()
    return configured_context


# ──────────────────────────────────────────────
# Guard Clauses
# ──────────────────────────────────────────────

class TestMessageGuardClauses:
    """Testes de validacao (early returns) do handle_message."""

    @pytest.mark.asyncio
    async def test_no_message(self, mock_update, configured_message_context):
        """Retorna cedo se nao houver mensagem."""
        mock_update.message = None
        await handle_message(mock_update, configured_message_context)
        groq = configured_message_context.bot_data["groq"]
        assert not groq.generate_reply.called

    @pytest.mark.asyncio
    async def test_empty_text(self, mock_update, configured_message_context):
        """Retorna cedo se o texto for vazio."""
        mock_update.message.text = ""
        await handle_message(mock_update, configured_message_context)
        groq = configured_message_context.bot_data["groq"]
        assert not groq.generate_reply.called

    @pytest.mark.asyncio
    async def test_command_prefix(self, mock_update, configured_message_context):
        """Retorna cedo se o texto comecar com /."""
        mock_update.message.text = "/start"
        await handle_message(mock_update, configured_message_context)
        groq = configured_message_context.bot_data["groq"]
        assert not groq.generate_reply.called

    @pytest.mark.asyncio
    async def test_missing_services(self, message_update, mock_context):
        """Mostra erro se servicos nao estiverem inicializados no bot_data."""
        await handle_message(message_update, mock_context)
        message_update.message.reply_text.assert_called_once()
        text = message_update.message.reply_text.call_args[0][0]
        assert "not ready" in text.lower()

    @pytest.mark.asyncio
    async def test_groq_failure(self, message_update, configured_message_context):
        """Mostra erro se o Groq falhar ao gerar resposta."""
        configured_message_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=None
        )
        await handle_message(message_update, configured_message_context)
        message_update.message.reply_text.assert_called_once()
        text = message_update.message.reply_text.call_args[0][0]
        assert "trouble thinking" in text.lower()


# ──────────────────────────────────────────────
# Message Flow
# ──────────────────────────────────────────────

class TestMessageFlow:
    """Testes do fluxo principal de processamento de mensagem."""

    @pytest.mark.asyncio
    async def test_sends_typing_action(self, message_update, configured_message_context):
        """Envia acao de typing antes de processar."""
        await handle_message(message_update, configured_message_context)
        message_update.message.chat.send_action.assert_called_once_with(action="typing")

    @pytest.mark.asyncio
    async def test_adds_user_message_to_history(self, message_update, configured_message_context):
        """Adiciona a mensagem do usuario ao historico da conversa."""
        await handle_message(message_update, configured_message_context)
        conv_mgr = configured_message_context.bot_data["conversation_mgr"]
        conv = conv_mgr.get_or_create(12345)
        history = conv.get_history()
        assert len(history) >= 1
        assert history[0] == ("user", "Hello! How are you?")

    @pytest.mark.asyncio
    async def test_calls_groq_with_history(self, message_update, configured_message_context):
        """Chama o Groq com o historico formatado e nivel do usuario."""
        await handle_message(message_update, configured_message_context)
        groq = configured_message_context.bot_data["groq"]
        groq.generate_reply.assert_called_once()
        call_kwargs = groq.generate_reply.call_args.kwargs
        assert "level" in call_kwargs
        assert call_kwargs["level"] == "A1"

    @pytest.mark.asyncio
    async def test_adds_assistant_message_on_success(self, message_update, configured_message_context):
        """Adiciona a resposta do assistente ao historico apos sucesso."""
        await handle_message(message_update, configured_message_context)
        conv_mgr = configured_message_context.bot_data["conversation_mgr"]
        conv = conv_mgr.get_or_create(12345)
        history = conv.get_history()
        assert len(history) == 2
        assert history[0] == ("user", "Hello! How are you?")
        assert history[1][0] == "assistant"
        assert history[1][1] == "Hello! How are you today? \U0001f60a"

    @pytest.mark.asyncio
    async def test_reply_sent_on_success(self, message_update, configured_message_context):
        """Envia a resposta de texto ao usuario."""
        await handle_message(message_update, configured_message_context)
        message_update.message.reply_text.assert_called()


# ──────────────────────────────────────────────
# Vocabulary Extraction and Saving
# ──────────────────────────────────────────────

class TestMessageVocabulary:
    """Testes de extracao e salvamento de vocabulario."""

    @pytest.mark.asyncio
    async def test_vocab_extracted_and_saved(self, message_update, configured_message_context):
        """Vocabulario extraido da resposta e salvo no banco."""
        groq_reply = (
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n"
            "Do you eat breakfast?"
        )
        configured_message_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=groq_reply
        )
        await handle_message(message_update, configured_message_context)
        db = configured_message_context.bot_data["db"]
        db.save_vocab.assert_called_once()
        call_kwargs = db.save_vocab.call_args.kwargs
        assert call_kwargs["word"] == "breakfast"
        assert call_kwargs["translation"] == "cafe da manha"
        assert call_kwargs["context"] == "I eat breakfast at 7am."
        assert call_kwargs["level"] == "A1"

    @pytest.mark.asyncio
    async def test_vocab_clean_reply_used(self, message_update, configured_message_context):
        """O texto exibido usa a versao limpa (sem marcadores de vocabulario)."""
        groq_reply = (
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n"
            "Do you eat breakfast?"
        )
        configured_message_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=groq_reply
        )
        await handle_message(message_update, configured_message_context)
        text = message_update.message.reply_text.call_args[0][0]
        assert "Do you eat breakfast?" in text
        assert "NEW_WORD" not in text
        assert "EXAMPLE" not in text

    @pytest.mark.asyncio
    async def test_vocab_save_error_does_not_block(self, message_update, configured_message_context):
        """Erro ao salvar vocabulario nao interrompe o fluxo."""
        groq_reply = (
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n"
            "Do you eat breakfast?"
        )
        configured_message_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=groq_reply
        )
        configured_message_context.bot_data["db"].save_vocab = AsyncMock(
            side_effect=Exception("DB error")
        )
        await handle_message(message_update, configured_message_context)
        # reply_text deve ter sido chamado com o texto limpo mesmo apos erro no vocab
        text = message_update.message.reply_text.call_args[0][0]
        assert "Do you eat breakfast?" in text


# ──────────────────────────────────────────────
# Audio Generation
# ──────────────────────────────────────────────

class TestMessageAudio:
    """Testes de geracao de audio via TTSOrchestrator."""

    @pytest.mark.asyncio
    async def test_audio_generated_with_orchestrator(self, message_update, configured_message_context):
        """TTSOrchestrator e chamado para gerar audio."""
        await handle_message(message_update, configured_message_context)
        tts = configured_message_context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_voice_and_text_sent_when_audio_success(self, message_update, configured_message_context):
        """Texto e audio sao enviados quando o TTS gera audio com sucesso."""
        await handle_message(message_update, configured_message_context)
        message_update.message.reply_text.assert_called_once()
        message_update.message.reply_voice.assert_called_once()

    @pytest.mark.asyncio
    async def test_buttons_on_voice_note(self, message_update, configured_message_context):
        """Botoes vao no reply_voice, nao no reply_text."""
        await handle_message(message_update, configured_message_context)
        # reply_text nao deve ter reply_markup (botoes vao na voz)
        text_kwargs = message_update.message.reply_text.call_args.kwargs
        assert "reply_markup" not in text_kwargs
        # reply_voice deve ter botoes
        message_update.message.reply_voice.assert_called_once()
        voice_kwargs = message_update.message.reply_voice.call_args.kwargs
        assert "reply_markup" in voice_kwargs

    @pytest.mark.asyncio
    async def test_only_text_when_no_tts_orchestrator(self, message_update, configured_message_context):
        """Apenas texto e enviado quando nao ha TTSOrchestrator."""
        del configured_message_context.bot_data["tts_orchestrator"]
        await handle_message(message_update, configured_message_context)
        message_update.message.reply_text.assert_called_once()
        message_update.message.reply_voice.assert_not_called()
        # reply_text deve ter reply_markarkup quando nao ha audio
        text_kwargs = message_update.message.reply_text.call_args.kwargs
        assert "reply_markup" in text_kwargs

    @pytest.mark.asyncio
    async def test_audio_tip_when_custom_voice_fails(self, message_update, configured_message_context):
        """Mostra dica de audio quando voz personalizada falha."""
        configured_message_context.user_data["voice_id"] = "custom_voice"
        configured_message_context.bot_data["tts_orchestrator"].generate_audio = AsyncMock(
            return_value=None
        )
        await handle_message(message_update, configured_message_context)
        tip_calls = [
            c for c in message_update.message.reply_text.call_args_list
            if "tip" in str(c.args[0]).lower()
        ]
        assert len(tip_calls) == 1
        tip_text = tip_calls[0][0][0]
        assert "voice you selected" in tip_text.lower()
        assert "/voice" in tip_text

    @pytest.mark.asyncio
    async def test_no_audio_tip_when_default_voice(self, message_update, configured_message_context):
        """Nao mostra dica de audio quando a voz padrao falha."""
        configured_message_context.bot_data["tts_orchestrator"].generate_audio = AsyncMock(
            return_value=None
        )
        await handle_message(message_update, configured_message_context)
        tip_calls = [
            c for c in message_update.message.reply_text.call_args_list
            if "tip" in str(c.args[0]).lower()
        ]
        assert len(tip_calls) == 0

    @pytest.mark.asyncio
    async def test_speed_and_voice_from_user_data(self, message_update, configured_message_context):
        """Voice_id e speed de user_data sao passados ao TTSOrchestrator."""
        configured_message_context.user_data["voice_id"] = "asteria"
        configured_message_context.user_data["tts_speed"] = 0.75
        await handle_message(message_update, configured_message_context)
        tts = configured_message_context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()
        assert tts.generate_audio.call_args.kwargs.get("voice_id") == "asteria"
        assert tts.generate_audio.call_args.kwargs.get("speed") == 0.75


# ──────────────────────────────────────────────
# Rate Limiter
# ──────────────────────────────────────────────

class TestMessageRateLimiter:
    """Testes do rate limiter no fluxo de mensagem."""

    @pytest.mark.asyncio
    async def test_rate_limiter_warning_shown(self, message_update, configured_message_context):
        """Aviso do rate limiter e enviado ao usuario."""
        configured_message_context.bot_data["rate_limiter"].check_and_increment = MagicMock(
            return_value={
                "allowed": False,
                "current": 101,
                "limit": 100,
                "remaining": 0,
                "warning": "You've reached your daily limit. Please try again tomorrow!",
            }
        )
        await handle_message(message_update, configured_message_context)
        warning_calls = [
            c for c in message_update.message.reply_text.call_args_list
            if "daily limit" in str(c.args[0]).lower()
        ]
        assert len(warning_calls) == 1

    @pytest.mark.asyncio
    async def test_no_warning_when_under_limit(self, message_update, configured_message_context):
        """Nenhum aviso e enviado quando o usuario esta dentro do limite."""
        await handle_message(message_update, configured_message_context)
        warning_calls = [
            c for c in message_update.message.reply_text.call_args_list
            if "limit" in str(c.args[0]).lower() or "warning" in str(c.args[0]).lower()
        ]
        assert len(warning_calls) == 0


# ──────────────────────────────────────────────
# Button Cleanup
# ──────────────────────────────────────────────

class TestButtonCleanup:
    """Testes de limpeza e rastreamento de botoes."""

    @pytest.mark.asyncio
    async def test_old_buttons_cleaned(self, message_update, configured_message_context):
        """Botoes de mensagens anteriores sao removidos."""
        configured_message_context.user_data["button_msg_ids"] = [50, 51]
        await handle_message(message_update, configured_message_context)
        bot = configured_message_context.bot
        assert bot.edit_message_reply_markup.call_count == 2
        # Verifica que os IDs antigos foram passados
        calls = bot.edit_message_reply_markup.call_args_list
        assert calls[0].kwargs["message_id"] == 50
        assert calls[1].kwargs["message_id"] == 51

    @pytest.mark.asyncio
    async def test_button_ids_tracked(self, message_update, configured_message_context):
        """O message_id da mensagem de voz e rastreado em button_msg_ids."""
        await handle_message(message_update, configured_message_context)
        assert "button_msg_ids" in configured_message_context.user_data
        assert len(configured_message_context.user_data["button_msg_ids"]) == 1
        expected_id = message_update.message.reply_voice.return_value.message_id
        assert configured_message_context.user_data["button_msg_ids"][0] == expected_id
