"""
LinguaBot --- TTS Orchestrator

Servico unificado de geracao de audio que coordena:
  1. Deepgram Aura (TTS primario, 4 vozes)
  2. ElevenLabs (fallback, voz Rachel)

Centraliza a logica de fallback e resolucao de velocidade,
eliminando a duplicacao entre audio.py e message.py.
"""

from __future__ import annotations

import logging

from bot.services.deepgram_tts import DEFAULT_VOICE_ID, DeepgramTTSService
from bot.services.elevenlabs import ElevenLabsService

logger = logging.getLogger(__name__)


class TTSOrchestrator:
    """Coordena a geracao de audio entre Deepgram Aura (primario) e ElevenLabs (fallback).

    Uso nos handlers:
        tts: TTSOrchestrator = context.bot_data.get("tts_orchestrator")
        audio_bytes = await tts.generate_audio(text, voice_id=..., speed=...)

    Se ambos provedores falharem, retorna None (handler decide como proceder).
    """

    def __init__(
        self,
        deepgram_tts: DeepgramTTSService | None = None,
        elevenlabs: ElevenLabsService | None = None,
    ):
        self.deepgram_tts = deepgram_tts
        self.elevenlabs = elevenlabs

    async def generate_audio(
        self,
        text: str,
        voice_id: str = DEFAULT_VOICE_ID,
        speed: float = 1.0,
    ) -> bytes | None:
        """Gera audio com fallback em cascata: Deepgram -> ElevenLabs -> None.

        Args:
            text: Texto a ser convertido em audio.
            voice_id: Voz Deepgram Aura (ignorada no ElevenLabs).
            speed: Multiplicador de velocidade (0.75 a 1.25).

        Returns:
            Bytes MP3 do audio, ou None se ambos provedores falharem.
        """
        # 1. Tenta Deepgram Aura (primario)
        if self.deepgram_tts:
            audio = await self.deepgram_tts.generate_speech(
                text, voice_id=voice_id, speed=speed,
            )
            if audio is not None:
                return audio

        # 2. Fallback: ElevenLabs
        if self.elevenlabs:
            logger.info("Deepgram Aura falhou, usando ElevenLabs fallback")
            audio = await self.elevenlabs.generate_speech(text, speed=speed)
            if audio is not None:
                return audio

        # 3. Ambos falharam
        logger.warning("Ambos TTS falharam — resposta sem audio")
        return None
