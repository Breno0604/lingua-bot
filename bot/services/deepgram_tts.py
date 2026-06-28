"""
LinguaBot --- Deepgram Aura TTS Service

Servico primario de Text-to-Speech usando Deepgram Aura.
Fornece 4 vozes (2 femininas, 2 masculinas) com tom calmo e claro.

Fluxo:
  1. Recebe texto e voice_id
  2. Chama Deepgram Aura TTS API (speak.v1.audio.generate)
  3. Retorna bytes do audio (MP3)
  4. Se falhar, retorna None (quem chama deve usar fallback)
"""

import logging
from typing import Optional

from deepgram import DeepgramClient

from bot.audio_cache import AudioCache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Vozes Deepgram Aura
# ──────────────────────────────────────────────
# Todas sao vozes do modelo aura-2, otimizadas para conversacao.
# Selecionadas: 2 femininas (calmas e claras) + 2 masculinas (calmos e profissionais)

VOICES: list[tuple[str, str, str]] = [
    ("aura-2-thalia-en", "Thalia", "Feminine, clear, confident, energetic"),
    ("aura-2-odysseus-en", "Odysseus", "Masculine, calm, smooth, professional"),
    ("aura-2-helena-en", "Helena", "Feminine, caring, natural, friendly"),
    ("aura-2-mars-en", "Mars", "Masculine, smooth, patient, trustworthy, baritone"),
]

VOICE_MAP: dict[str, tuple[str, str]] = {vid: (name, desc) for vid, name, desc in VOICES}
VOICE_IDS: list[str] = [vid for vid, _, _ in VOICES]
DEFAULT_VOICE_ID: str = VOICES[0][0]  # Thalia

MAX_CHARS = 500  # limite por requisicao (Deepgram nao tem limite mensal publico)


class DeepgramTTSService:
    """Cliente Deepgram Aura TTS.

    Gera audio a partir de texto usando Deepgram Aura (modelo aura-2).
    Voce pode escolher entre 4 vozes (2F + 2M) com tom calmo e claro.
    """

    def __init__(self, api_key: str, audio_cache: AudioCache = None):
        self.api_key = api_key
        self.cache = audio_cache or AudioCache()
        self._client: Optional[DeepgramClient] = None
        self.max_text_chars = 150  # Deepgram Aura aceita textos mais longos que ElevenLabs

    def _get_client(self) -> DeepgramClient:
        if self._client is None:
            self._client = DeepgramClient(api_key=self.api_key)
        return self._client

    def _truncate_text(self, text: str, max_chars: int = 150) -> str:
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

    async def generate_speech(self, text: str, voice_id: str = DEFAULT_VOICE_ID) -> Optional[bytes]:
        """Gera audio a partir do texto usando Deepgram Aura.

        Args:
            text: Texto a ser convertido em audio.
            voice_id: ID da voz (ex: aura-2-thalia-en).

        Returns:
            Bytes do audio (MP3), ou None se falhou.
        """
        # 1. Trunca texto
        truncated = self._truncate_text(text, max_chars=self.max_text_chars)

        # 2. Verifica cache
        cache_key = f"dg:{voice_id}:{truncated}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # 3. Chama Deepgram Aura
        audio = await self._try_deepgram(truncated, voice_id=voice_id)
        if audio is not None:
            self.cache.set(cache_key, audio)
            return audio

        logger.error("Deepgram Aura TTS falhou para voz: %s", voice_id)
        return None

    async def _try_deepgram(self, text: str, voice_id: str = DEFAULT_VOICE_ID) -> Optional[bytes]:
        """Tenta gerar audio com Deepgram Aura."""
        try:
            client = self._get_client()
            chunks = client.speak.v1.audio.generate(
                text=text,
                model=voice_id,
                encoding="mp3",
                container="none",
            )

            audio_bytes = b"".join(chunks)
            if audio_bytes:
                logger.info(
                    "Deepgram Aura OK (voice: %s, chars: %d)",
                    voice_id, len(text),
                )
                return audio_bytes

            logger.warning("Deepgram Aura retornou audio vazio (voice: %s)", voice_id)

        except Exception as e:
            logger.warning("Deepgram Aura falhou (voice: %s): %s", voice_id, e)

        return None
