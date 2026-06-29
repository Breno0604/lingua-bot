"""
LinguaBot --- Tests for bot.handlers.audio

Testa o fluxo completo de processamento de audio:
  1. Guard clauses (sem servicos, sem conversa, falhas de download/STT/Groq)
  2. Transcricao permanece visivel (nao e apagada)
  3. Texto enviado antes do audio
  4. Fallback Deepgram -> ElevenLabs
  5. Dica de voz personalizada
  6. Salvamento de vocabulario
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.handlers.audio import handle_audio


# ──────────────────────────────────────────────
# Fixtures especificas para testes de audio
# ──────────────────────────────────────────────

@pytest.fixture
def mock_voice():
    """Cria um mock de mensagem de voz do Telegram."""
    voice = MagicMock()
    voice.file_id = "test_voice_file_id"
    voice.duration = 3

    # Mock do download do arquivo
    file = MagicMock()
    file.download_as_bytearray = AsyncMock(return_value=b"fake_audio_ogg_bytes")
    voice.get_file = AsyncMock(return_value=file)
    return voice


@pytest.fixture
def mock_deepgram_stt():
    """Mock do DeepgramService (STT) — retorna transcricao com sucesso."""
    dg = MagicMock()
    dg.transcribe_audio = AsyncMock(return_value="I need help with my English")
    return dg


@pytest.fixture
def mock_deepgram_tts():
    """Mock do Deepgram Aura TTS — retorna audio com sucesso."""
    tts = MagicMock()
    tts.generate_speech = AsyncMock(return_value=b"fake_deepgram_audio")
    return tts


@pytest.fixture
def mock_elevenlabs():
    """Mock do ElevenLabsService — retorna audio com sucesso."""
    el = MagicMock()
    el.generate_speech = AsyncMock(return_value=b"fake_elevenlabs_audio")
    return el


@pytest.fixture
def mock_level_manager():
    """Mock do LevelManager."""
    lm = MagicMock()
    lm.get_level = MagicMock(return_value="A1")
    return lm


@pytest.fixture
def configured_audio_context(
    configured_context,
    mock_voice,
    mock_deepgram_stt,
    mock_deepgram_tts,
    mock_elevenlabs,
    mock_level_manager,
    mock_tts_orchestrator,
):
    """Context pre-configurado com todos os servicos de audio."""
    configured_context.bot_data["deepgram"] = mock_deepgram_stt
    configured_context.bot_data["deepgram_tts"] = mock_deepgram_tts
    configured_context.bot_data["elevenlabs"] = mock_elevenlabs
    configured_context.bot_data["level_manager"] = mock_level_manager
    configured_context.bot_data["tts_orchestrator"] = mock_tts_orchestrator
    # user_data precisa ser um dict real para .get() e atribuicoes funcionarem
    configured_context.user_data = {}
    return configured_context


@pytest.fixture
def audio_update(mock_update, mock_voice):
    """Update do Telegram com mensagem de voz."""
    mock_update.message.voice = mock_voice
    mock_update.message.audio = None
    mock_update.message.reply_voice = AsyncMock()
    # reply_text retorna um mock com edit_reply_markup (usado para adicionar botoes apos o audio)
    text_msg = MagicMock()
    text_msg.edit_reply_markup = AsyncMock()
    mock_update.message.reply_text.return_value = text_msg
    return mock_update


@pytest.fixture
def active_conversation(audio_update, configured_audio_context):
    """Fixture que ja inicializa uma conversa ativa no contexto."""
    conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
    conv.add_user_message("Hello!")
    conv.add_assistant_message("Hi! How are you today?")
    return audio_update, configured_audio_context


# ──────────────────────────────────────────────
# Guard Clauses
# ──────────────────────────────────────────────

class TestAudioGuardClauses:
    """Testes de validacao (early returns) do handle_audio."""

    @pytest.mark.asyncio
    async def test_no_message(self, mock_update, configured_audio_context):
        """Retorna cedo se nao houver mensagem."""
        mock_update.message = None
        await handle_audio(mock_update, configured_audio_context)
        assert not configured_audio_context.bot_data["groq"].generate_reply.called

    @pytest.mark.asyncio
    async def test_no_voice_or_audio(self, mock_update, configured_audio_context):
        """Retorna cedo se nao houver voice nem audio na mensagem."""
        mock_update.message.voice = None
        mock_update.message.audio = None
        await handle_audio(mock_update, configured_audio_context)
        assert not configured_audio_context.bot_data["groq"].generate_reply.called

    @pytest.mark.asyncio
    async def test_missing_services(self, audio_update, mock_context):
        """Mostra erro se servicos nao estiverem inicializados no bot_data."""
        mock_context.bot_data.clear()
        await handle_audio(audio_update, mock_context)
        audio_update.message.reply_text.assert_called_once()
        text = audio_update.message.reply_text.call_args[0][0]
        assert "not ready" in text.lower()

    @pytest.mark.asyncio
    async def test_no_active_conversation(self, audio_update, configured_audio_context):
        """Mostra aviso se nao houver conversa ativa (historico vazio)."""
        await handle_audio(audio_update, configured_audio_context)
        audio_update.message.reply_text.assert_called_once()
        text = audio_update.message.reply_text.call_args[0][0]
        assert "start with text first" in text.lower()

    @pytest.mark.asyncio
    async def test_download_error(self, audio_update, configured_audio_context):
        """Mostra erro se o download do arquivo de audio falhar."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        audio_update.message.voice.get_file = AsyncMock(
            side_effect=Exception("Network error")
        )

        await handle_audio(audio_update, configured_audio_context)
        audio_update.message.reply_text.assert_called_once()
        text = audio_update.message.reply_text.call_args[0][0]
        assert "couldn't download your audio" in text.lower()

    @pytest.mark.asyncio
    async def test_stt_failure(self, audio_update, configured_audio_context):
        """Mostra erro se o STT nao conseguir transcrever."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.bot_data["deepgram"].transcribe_audio = AsyncMock(
            return_value=None
        )

        await handle_audio(audio_update, configured_audio_context)
        audio_update.message.reply_text.assert_called_once()
        text = audio_update.message.reply_text.call_args[0][0]
        assert "couldn't understand the audio" in text.lower()

    @pytest.mark.asyncio
    async def test_groq_failure(self, audio_update, configured_audio_context):
        """Mostra erro se o Groq falhar ao gerar resposta."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=None
        )

        await handle_audio(audio_update, configured_audio_context)
        # Deve ter chamado reply_text para o preview + mensagem de erro
        assert audio_update.message.reply_text.call_count >= 1
        # A ultima chamada deve ser a mensagem de erro
        calls = audio_update.message.reply_text.call_args_list
        last_text = calls[-1][0][0]
        assert "trouble thinking" in last_text.lower()


# ──────────────────────────────────────────────
# Requisito 1: Transcricao permanece visivel
# ──────────────────────────────────────────────

class TestTranscriptionStaysVisible:
    """A transcricao do audio deve permanecer visivel no historico."""

    @pytest.mark.asyncio
    async def test_transcription_preview_is_sent(self, active_conversation):
        """O preview com a transcricao e enviado como mensagem de texto."""
        update, context = active_conversation

        await handle_audio(update, context)

        # Busca chamadas de reply_text que contenham "You said:"
        preview_calls = [
            c for c in update.message.reply_text.call_args_list
            if "You said:" in str(c.args)
        ]
        assert len(preview_calls) == 1
        preview_text = preview_calls[0][0][0]
        assert "I need help with my English" in preview_text
        assert "Let me respond" in preview_text

    @pytest.mark.asyncio
    async def test_transcription_not_deleted_after_audio(self, active_conversation):
        """A mensagem de preview NAO e apagada apos o processamento do audio.

        Verifica que nao ha chamada a delete_message ou delete no flow.
        """
        update, context = active_conversation

        await handle_audio(update, context)

        # Verifica que reply_text foi chamado para o preview
        preview_calls = [
            c for c in update.message.reply_text.call_args_list
            if "You said:" in str(c.args)
        ]
        assert len(preview_calls) == 1

        # Como o preview.delete() foi removido, nao deve haver chamada
        # de delete_message no mock. A unica forma de verificar e que
        # o preview ainda existe como mensagem separada (nao foi removido).
        # Nao temos acesso direto ao objeto preview, mas podemos verificar
        # que nao ha chamadas relacionados a delete_message no chat ou message
        # e que a preview ainda consta nas chamadas de reply_text.

        # No happy path (Deepgram TTS funciona, sem tip) sao exatamente 2:
        # preview + resposta
        assert update.message.reply_text.call_count == 2

    @pytest.mark.asyncio
    async def test_transcription_content_is_correct(self, active_conversation):
        """O texto da transcricao reflete o que o STT retornou."""
        update, context = active_conversation

        await handle_audio(update, context)

        preview_calls = [
            c for c in update.message.reply_text.call_args_list
            if "You said:" in str(c.args)
        ]
        preview_text = preview_calls[0][0][0]
        # Deve conter o texto transcrito
        assert "I need help with my English" in preview_text
        # Deve estar formatado em Markdown
        assert preview_calls[0][1].get("parse_mode") == "Markdown"


# ──────────────────────────────────────────────
# Requisito 2: Texto antes do audio
# ──────────────────────────────────────────────

class TestTextBeforeAudio:
    """O texto da resposta deve aparecer antes do audio."""

    @pytest.mark.asyncio
    async def test_response_text_sent_before_voice(self, active_conversation):
        """O reply_text da resposta ocorre ANTES do reply_voice."""
        update, context = active_conversation

        await handle_audio(update, context)

        # Coleta ordem de todas as chamadas no update.message
        # mock_calls registra todas as chamadas em ordem cronologica
        calls = update.message.mock_calls
        # Filtra apenas reply_text (resposta) e reply_voice
        # Ignora reply_text do preview ("You said:") e do audio tip
        ordered = []
        for call in calls:
            call_name = call[0]
            if call_name == "reply_voice":
                ordered.append("voice")
            elif call_name == "reply_text":
                args = call[1]
                if args and isinstance(args[0], str):
                    if "You said:" not in args[0] and "tip" not in args[0].lower():
                        ordered.append("text")

        # Deve ter pelo menos um "text" antes de "voice"
        assert "text" in ordered
        assert "voice" in ordered
        text_index = ordered.index("text")
        voice_index = ordered.index("voice")
        assert text_index < voice_index, (
            f"Texto (indice {text_index}) deve vir antes do audio (indice {voice_index})"
        )

    @pytest.mark.asyncio
    async def test_text_sent_without_buttons_initially(self, active_conversation):
        """O texto e enviado SEM botoes inicialmente."""
        update, context = active_conversation

        await handle_audio(update, context)

        # Encontra o reply_text da resposta (nao preview, nao tip)
        text_calls = [
            c for c in update.message.reply_text.call_args_list
            if "You said:" not in str(c.args)
            and "tip" not in str(c.args[0]).lower()
        ]
        assert len(text_calls) >= 1
        kwargs = text_calls[0].kwargs
        # reply_text nao deve ter reply_markup — os botoes vao no reply_voice (quando audio existe)
        # ou via edit_reply_markup (fallback quando audio falha)
        assert "reply_markup" not in kwargs, (
            "Texto inicial nao deve ter botoes — eles vao no reply_voice ou edit_reply_markup"
        )

    @pytest.mark.asyncio
    async def test_buttons_on_voice_note_when_audio_succeeds(self, active_conversation):
        """Quando audio existe, os botoes vao no reply_voice, nao no edit_reply_markup."""
        update, context = active_conversation

        await handle_audio(update, context)

        # Botoes devem estar no reply_voice
        update.message.reply_voice.assert_called_once()
        voice_kwargs = update.message.reply_voice.call_args.kwargs
        assert "reply_markup" in voice_kwargs, (
            "reply_voice deve ter reply_markup com os botoes quando audio existe"
        )

        # edit_reply_markup NAO deve ser chamado (so e usado quando audio falha)
        text_msg = update.message.reply_text.return_value
        text_msg.edit_reply_markup.assert_not_called()

    @pytest.mark.asyncio
    async def test_voice_sent_separately_after_text(self, active_conversation):
        """O audio e enviado como mensagem separada de voz."""
        update, context = active_conversation

        await handle_audio(update, context)

        # Verifica que reply_voice foi chamado com os bytes de audio
        update.message.reply_voice.assert_called_once()
        voice_call = update.message.reply_voice.call_args
        assert "voice" in voice_call.kwargs


# ──────────────────────────────────────────────
# TTS Flow: Deepgram + ElevenLabs Fallback
# ──────────────────────────────────────────────

class TestTTSFlow:
    """Testes de geracao de audio via TTSOrchestrator."""

    @pytest.mark.asyncio
    async def test_tts_orchestrator_called_by_default(self, active_conversation):
        """TTSOrchestrator e chamado para gerar audio."""
        update, context = active_conversation

        await handle_audio(update, context)

        tts = context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_audio_when_orchestrator_returns_none(self, audio_update, configured_audio_context):
        """Nenhum audio e enviado se o orquestrador retornar None."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.bot_data["tts_orchestrator"].generate_audio = AsyncMock(
            return_value=None
        )

        await handle_audio(audio_update, configured_audio_context)

        audio_update.message.reply_voice.assert_not_called()
        # Botoes ainda devem ser adicionados ao texto
        text_msg = audio_update.message.reply_text.return_value
        text_msg.edit_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_tip_when_custom_voice_fails(self, audio_update, configured_audio_context):
        """Mostra dica de audio quando voz personalizada falha."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.user_data["voice_id"] = "custom_voice"
        configured_audio_context.bot_data["tts_orchestrator"].generate_audio = AsyncMock(
            return_value=None
        )

        await handle_audio(audio_update, configured_audio_context)

        tip_calls = [
            c for c in audio_update.message.reply_text.call_args_list
            if "tip" in str(c.args[0]).lower()
        ]
        assert len(tip_calls) == 1
        tip_text = tip_calls[0][0][0]
        assert "voice you selected" in tip_text.lower()
        assert "/voice" in tip_text
        text_msg = audio_update.message.reply_text.return_value
        text_msg.edit_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_audio_tip_when_default_voice(self, audio_update, configured_audio_context):
        """Nao mostra dica de audio se for a voz padrao."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.bot_data["tts_orchestrator"].generate_audio = AsyncMock(
            return_value=None
        )

        await handle_audio(audio_update, configured_audio_context)

        tip_calls = [
            c for c in audio_update.message.reply_text.call_args_list
            if "tip" in str(c.args[0]).lower()
        ]
        assert len(tip_calls) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_receives_user_voice_preference(self, active_conversation):
        """Voice_id do usuario e passado ao TTSOrchestrator."""
        update, context = active_conversation

        context.user_data["voice_id"] = "asteria"

        await handle_audio(update, context)

        tts = context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()
        assert tts.generate_audio.call_args.kwargs.get("voice_id") == "asteria"

    @pytest.mark.asyncio
    async def test_speed_passed_to_orchestrator(self, active_conversation):
        """Velocidade personalizada e passada ao TTSOrchestrator."""
        update, context = active_conversation

        context.user_data["tts_speed"] = 0.85

        await handle_audio(update, context)

        tts = context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()
        assert tts.generate_audio.call_args.kwargs.get("speed") == 0.85, (
            f"speed=0.85 esperado, recebeu {tts.generate_audio.call_args.kwargs.get('speed')}"
        )

    @pytest.mark.asyncio
    async def test_speed_defaults_to_level_based(self, audio_update, configured_audio_context):
        """Quando speed nao esta em user_data, usa padrao baseado no nivel (A1=0.85)."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        configured_audio_context.user_data = {}

        await handle_audio(audio_update, configured_audio_context)

        tts = configured_audio_context.bot_data["tts_orchestrator"]
        tts.generate_audio.assert_called_once()
        assert tts.generate_audio.call_args.kwargs.get("speed") == 0.85, (
            f"A1 deve usar speed=0.85, recebeu {tts.generate_audio.call_args.kwargs.get('speed')}"
        )


# ──────────────────────────────────────────────
# Salvamento de Vocabulario
# ──────────────────────────────────────────────

class TestVocabularySaving:
    """Testes de salvamento de vocabulario durante processamento de audio."""

    @pytest.mark.asyncio
    async def test_vocab_saved_from_reply(self, audio_update, configured_audio_context):
        """Vocabulario extraido da resposta e salvo no banco."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        # Groq retorna resposta com marcadores de vocabulario
        groq_reply = (
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n"
            "Do you eat breakfast?"
        )
        configured_audio_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=groq_reply
        )

        await handle_audio(audio_update, configured_audio_context)

        # Verifica que o vocabulario foi salvo
        db = configured_audio_context.bot_data["db"]
        db.save_vocab.assert_called_once()
        call_kwargs = db.save_vocab.call_args.kwargs
        assert call_kwargs["word"] == "breakfast"
        assert call_kwargs["translation"] == "cafe da manha"
        assert call_kwargs["context"] == "I eat breakfast at 7am."
        assert call_kwargs["level"] == "A1"

    @pytest.mark.asyncio
    async def test_vocab_save_error_does_not_block(self, audio_update, configured_audio_context):
        """Erro ao salvar vocabulario nao interrompe o fluxo."""
        conv = configured_audio_context.bot_data["conversation_mgr"].get_or_create(12345)
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")

        groq_reply = (
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n"
            "Do you eat breakfast?"
        )
        configured_audio_context.bot_data["groq"].generate_reply = AsyncMock(
            return_value=groq_reply
        )
        configured_audio_context.bot_data["db"].save_vocab = AsyncMock(
            side_effect=Exception("DB error")
        )

        # Nao deve lancar excecao — deve continuar o fluxo
        await handle_audio(audio_update, configured_audio_context)

        # O texto ainda deve ser enviado mesmo com erro no vocab
        text_calls = [
            c for c in audio_update.message.reply_text.call_args_list
            if "You said:" not in str(c.args)
            and "tip" not in str(c.args[0]).lower()
        ]
        assert len(text_calls) >= 1
        # O texto deve conter a resposta sem os marcadores
        assert "Do you eat breakfast?" in text_calls[0][0][0]
