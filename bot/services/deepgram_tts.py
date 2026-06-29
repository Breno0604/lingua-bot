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
from bot.utils.text_processing import clean_text, truncate_text

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

    async def generate_speech(self, text: str, voice_id: str = DEFAULT_VOICE_ID, speed: float = 1.0) -> Optional[bytes]:
        """Gera audio a partir do texto usando Deepgram Aura.

        Args:
            text: Texto a ser convertido em audio.
            voice_id: ID da voz (ex: aura-2-thalia-en).
            speed: Multiplicador de velocidade (0.75 a 1.25).
                   Se a API nao suportar, o parametro e ignorado.

        Returns:
            Bytes do audio (MP3), ou None se falhou.
        """
        # 1. Limpa emojis do texto (Deepgram tentaria pronuncia-los)
        cleaned = clean_text(text)
        if not cleaned:
            return None

        # 2. Trunca texto
        truncated = truncate_text(cleaned, max_chars=self.max_text_chars)

        # 3. Verifica cache
        cache_key = f"dg:{voice_id}:{speed}:{truncated}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # 3. Chama Deepgram Aura
        audio = await self._try_deepgram(truncated, voice_id=voice_id, speed=speed)
        if audio is not None:
            self.cache.set(cache_key, audio)
            return audio

        logger.error("Deepgram Aura TTS falhou para voz: %s", voice_id)
        return None

    async def _try_deepgram(self, text: str, voice_id: str = DEFAULT_VOICE_ID, speed: float = 1.0) -> Optional[bytes]:
        """Tenta gerar audio com Deepgram Aura.

        Se o parametro speed falhar (API nao suporta), tenta sem speed.
        """
        try:
            client = self._get_client()
            # Nota: encoding="mp3" NAO aceita parametro container
            kwargs = {
                "text": text,
                "model": voice_id,
                "encoding": "mp3",
            }
            # So inclui speed se diferente de 1.0 (para compatibilidade com API)
            if speed != 1.0:
                kwargs["speed"] = speed

            chunks = client.speak.v1.audio.generate(**kwargs)

            audio_bytes = b"".join(chunks)
            if audio_bytes:
                logger.info(
                    "Deepgram Aura OK (voice: %s, chars: %d, speed: %s)",
                    voice_id, len(text), speed,
                )
                return audio_bytes

            logger.warning("Deepgram Aura retornou audio vazio (voice: %s, speed: %s)", voice_id, speed)

        except Exception as e:
            logger.warning("Deepgram Aura falhou (voice: %s, speed: %s): %s", voice_id, speed, e)
            # Se falhou com speed != 1.0, tentar sem speed (fallback)
            if speed != 1.0:
                logger.info("Tentando Deepgram Aura sem speed parameter...")
                return await self._try_deepgram(text, voice_id=voice_id, speed=1.0)

        return None
