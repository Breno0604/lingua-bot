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
import re
from typing import Optional

from deepgram import DeepgramClient

from bot.audio_cache import AudioCache

logger = logging.getLogger(__name__)

# Padrao para remover emojis do texto antes de enviar para TTS
# Deepgram Aura e ElevenLabs tentam pronunciar emojis (ex: "\U0001f44d" -> "thumbs up")
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Simbolos e pictogramas
    "\U0001F680-\U0001F6FF"  # Transporte e mapas
    "\U0001F1E0-\U0001F1FF"  # Bandeiras (iOS)
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # Símbolos suplementares
    "\U0001FA00-\U0001FA6F"  # Símbolos de xadrez
    "\U0001FA70-\U0001FAFF"  # Símbolos diversos
    "\U00002600-\U000026FF"  # Miscelânea
    "\U0000FE00-\U0000FE0F"  # Variation selectors
    "\U0000200D"             # Zero-width joiner
    "]+",
    flags=re.UNICODE,
)

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

    def _clean_text(self, text: str) -> str:
        """Remove emojis e caracteres especiais que TTS tentaria pronunciar."""
        return EMOJI_PATTERN.sub("", text).strip()

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
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        # 2. Trunca texto
        truncated = self._truncate_text(cleaned, max_chars=self.max_text_chars)

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
