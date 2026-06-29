"""
LinguaBot --- ElevenLabs TTS Client (Fallback)

Gerador de audio secundario, usado como FALLBACK quando
o Deepgram Aura TTS falha.

Inclui:
  - Cache em memoria de audios gerados (por hash do texto)
  - Truncamento automatico (100 chars)
  - Modelo unico: Rachel (warm and clear)
"""

import logging
from typing import Optional

from elevenlabs.client import ElevenLabs as ElevenLabsClient

from bot.audio_cache import AudioCache
from bot.utils.text_processing import clean_text, truncate_text

logger = logging.getLogger(__name__)

# Voz unica de fallback
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # Rachel

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"
MAX_CHARS = 10000


class ElevenLabsService:
    """Cliente ElevenLabs TTS — usado como fallback do Deepgram Aura.

    Gera audio apenas com a voz Rachel (warm and clear).
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = AudioCache()
        self._client: Optional[ElevenLabsClient] = None
        self.monthly_chars_used = 0
        self.max_chars = MAX_CHARS
        self.max_text_chars = 100

    def _get_client(self) -> ElevenLabsClient:
        if self._client is None:
            self._client = ElevenLabsClient(api_key=self.api_key)
        return self._client

    async def generate_speech(self, text: str, speed: float = 1.0) -> Optional[bytes]:
        """Gera audio com ElevenLabs (voz Rachel).

        Fallback do Deepgram Aura. Usa cache e respeita limite mensal.

        Args:
            text: Texto a ser convertido em audio.
            speed: Multiplicador de velocidade (0.75 a 1.25).
                   Se a API nao suportar, o parametro e ignorado.

        Returns:
            Bytes MP3, ou None se falhou.
        """
        # 1. Remove emojis (ElevenLabs tentaria pronuncia-los)
        cleaned = clean_text(text)
        if not cleaned:
            return None

        # 2. Trunca
        truncated = truncate_text(cleaned, max_chars=self.max_text_chars)

        # 2. Cache
        cache_key = f"el:{speed}:{truncated}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # 3. Verifica cota
        if self.monthly_chars_used >= self.max_chars:
            logger.warning("ElevenLabs: cota mensal excedida (%d chars)", self.max_chars)
            return None

        # 4. Gera
        audio = await self._try_elevenlabs(truncated, speed=speed)
        if audio is not None:
            self.cache.set(cache_key, audio)
            return audio

        return None

    async def _try_elevenlabs(self, text: str, speed: float = 1.0) -> Optional[bytes]:
        """Tenta gerar audio com ElevenLabs Rachel.

        Suporta parametro speed se o modelo aceitar.
        """
        try:
            client = self._get_client()
            kwargs = {
                "voice_id": DEFAULT_VOICE_ID,
                "text": text,
                "model_id": MODEL_ID,
                "output_format": OUTPUT_FORMAT,
            }
            # Speed e um parametro opcional no modelo ElevenLabs
            if speed != 1.0:
                kwargs["speed"] = speed

            chunks = client.text_to_speech.convert(**kwargs)

            audio_bytes = b"".join(chunks)
            if audio_bytes:
                logger.info("ElevenLabs fallback OK (Rachel, chars: %d, speed: %s)", len(text), speed)
                self.monthly_chars_used += len(text)
                return audio_bytes

            logger.warning("ElevenLabs retornou audio vazio")

        except Exception as e:
            logger.warning("ElevenLabs falhou: %s", e)

        return None
