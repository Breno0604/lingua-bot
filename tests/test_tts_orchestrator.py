"""
LinguaBot --- Tests for bot.services.tts_orchestrator

Testa o TTSOrchestrator que coordena Deepgram Aura (primario) + ElevenLabs (fallback).

Cenarios:
  - Deepgram funciona -> retorna audio do Deepgram
  - Deepgram falha, ElevenLabs funciona -> retorna audio do ElevenLabs
  - Ambos falham -> retorna None
  - Servicos ausentes (None) -> comportamento graceful
  - Speed e voice_id sao repassados corretamente
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.services.tts_orchestrator import TTSOrchestrator
from bot.services.deepgram_tts import DEFAULT_VOICE_ID


@pytest.fixture
def mock_deepgram():
    """Mock do DeepgramTTSService que retorna audio com sucesso."""
    dg = MagicMock()
    dg.generate_speech = AsyncMock(return_value=b"deepgram_audio_bytes")
    return dg


@pytest.fixture
def mock_elevenlabs():
    """Mock do ElevenLabsService que retorna audio com sucesso."""
    el = MagicMock()
    el.generate_speech = AsyncMock(return_value=b"elevenlabs_audio_bytes")
    return el


class TestTTSOrchestrator:
    """Testes unitarios do TTSOrchestrator."""

    @pytest.mark.asyncio
    async def test_deepgram_returns_audio(self, mock_deepgram, mock_elevenlabs):
        """Deepgram retorna audio -> retorna o audio do Deepgram."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio == b"deepgram_audio_bytes"
        mock_deepgram.generate_speech.assert_called_once()
        mock_elevenlabs.generate_speech.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_elevenlabs_when_deepgram_fails(self, mock_deepgram, mock_elevenlabs):
        """Deepgram falha (None), ElevenLabs funciona -> retorna audio do ElevenLabs."""
        mock_deepgram.generate_speech = AsyncMock(return_value=None)

        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio == b"elevenlabs_audio_bytes"
        mock_deepgram.generate_speech.assert_called_once()
        mock_elevenlabs.generate_speech.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_fail_return_none(self, mock_deepgram, mock_elevenlabs):
        """Ambos provedores retornam None -> orquestrador retorna None."""
        mock_deepgram.generate_speech = AsyncMock(return_value=None)
        mock_elevenlabs.generate_speech = AsyncMock(return_value=None)

        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio is None
        mock_deepgram.generate_speech.assert_called_once()
        mock_elevenlabs.generate_speech.assert_called_once()

    @pytest.mark.asyncio
    async def test_deepgram_none_elevenlabs_works(self, mock_elevenlabs):
        """deepgram_tts=None (nao configurado), ElevenLabs funciona."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=None,
            elevenlabs=mock_elevenlabs,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio == b"elevenlabs_audio_bytes"
        mock_elevenlabs.generate_speech.assert_called_once()

    @pytest.mark.asyncio
    async def test_elevenlabs_none_deepgram_works(self, mock_deepgram):
        """elevenlabs=None (nao configurado), Deepgram funciona."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=None,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio == b"deepgram_audio_bytes"
        mock_deepgram.generate_speech.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_none_return_none(self):
        """Ambos None -> retorna None sem erros."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=None,
            elevenlabs=None,
        )

        audio = await orchestrator.generate_audio("Hello world")

        assert audio is None

    @pytest.mark.asyncio
    async def test_speed_passed_to_deepgram(self, mock_deepgram, mock_elevenlabs):
        """Speed e repassado ao Deepgram.generate_speech."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        await orchestrator.generate_audio("Hello world", speed=0.85)

        mock_deepgram.generate_speech.assert_called_once()
        kwargs = mock_deepgram.generate_speech.call_args.kwargs
        assert kwargs.get("speed") == 0.85

    @pytest.mark.asyncio
    async def test_speed_passed_to_elevenlabs_fallback(self, mock_deepgram, mock_elevenlabs):
        """Speed e repassado ao ElevenLabs quando Deepgram falha."""
        mock_deepgram.generate_speech = AsyncMock(return_value=None)

        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        await orchestrator.generate_audio("Hello world", speed=0.75)

        mock_elevenlabs.generate_speech.assert_called_once()
        kwargs = mock_elevenlabs.generate_speech.call_args.kwargs
        assert kwargs.get("speed") == 0.75

    @pytest.mark.asyncio
    async def test_voice_id_passed_to_deepgram(self, mock_deepgram, mock_elevenlabs):
        """Voice_id e repassado ao Deepgram.generate_speech."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        await orchestrator.generate_audio("Hello world", voice_id="custom_voice")

        mock_deepgram.generate_speech.assert_called_once()
        kwargs = mock_deepgram.generate_speech.call_args.kwargs
        assert kwargs.get("voice_id") == "custom_voice"

    @pytest.mark.asyncio
    async def test_default_voice_id(self, mock_deepgram, mock_elevenlabs):
        """Quando voice_id nao informado, usa DEFAULT_VOICE_ID."""
        orchestrator = TTSOrchestrator(
            deepgram_tts=mock_deepgram,
            elevenlabs=mock_elevenlabs,
        )

        await orchestrator.generate_audio("Hello world")

        mock_deepgram.generate_speech.assert_called_once()
        kwargs = mock_deepgram.generate_speech.call_args.kwargs
        assert kwargs.get("voice_id") == DEFAULT_VOICE_ID
