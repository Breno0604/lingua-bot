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
import re
from typing import Optional

from elevenlabs.client import ElevenLabs as ElevenLabsClient

from bot.audio_cache import AudioCache

logger = logging.getLogger(__name__)

# Mesmo padrao usado no DeepgramTTSService
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)

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

    def _clean_text(self, text: str) -> str:
        """Remove emojis que o TTS tentaria pronunciar."""
        return EMOJI_PATTERN.sub("", text).strip()

    def _truncate_text(self, text: str, max_chars: int = 100) -> str:
        """Trunca o texto mantendo a frase completa."""
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars // 2:
            return truncated[: last_period + 1].strip()

        last_space = truncated.rfind(" ")
        if last_space > max_chars // 2:
            return truncated[:last_space].strip() + "."

        return truncated.strip() + "."

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
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        # 2. Trunca
        truncated = self._truncate_text(cleaned, max_chars=self.max_text_chars)

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
