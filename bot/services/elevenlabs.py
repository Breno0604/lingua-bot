"""
LinguaBot --- ElevenLabs TTS Client

Gera audio a partir de texto usando ElevenLabs API.
Inclui:
  - Fallback automatico para Deepgram TTS quando limite e excedido
  - Cache em memoria de audios gerados (por hash do texto)
  - Truncamento automatico para 100 caracteres
"""

import logging
from typing import Optional

from elevenlabs.client import ElevenLabs as ElevenLabsClient

from bot.audio_cache import AudioCache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Vozes disponiveis
# ──────────────────────────────────────────────
# Cada entrada: (voice_id, nome_curto, descricao)
VOICES: list[tuple[str, str, str]] = [
    ("JBFqnCBsd6RMkjVDRZzb", "Rachel", "Warm and clear (default)"),
    ("XJVfsOvSwUXluggMM5Jj", "Stephanie v2", "Confident, clear and calm"),
    ("RaFzMbMIfqBcIurH6XF9", "Eryn", "Informative, neutral and measured"),
    ("bbGtsRRKUfYO634UxSjz", "Leo v2", "Technical and precise"),
    ("tCgAUbeV0tdD1S2yFoCx", "Jerry B.", "Instructional and tutorial"),
]

# Mapa voice_id -> (nome, descricao) para lookup rapido
VOICE_MAP: dict[str, tuple[str, str]] = {vid: (name, desc) for vid, name, desc in VOICES}
VOICE_IDS = [vid for vid, _, _ in VOICES]
DEFAULT_VOICE_ID = VOICES[0][0]  # Rachel

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"
MAX_CHARS = 10000


class ElevenLabsService:
    """Cliente ElevenLabs TTS com fallback para Deepgram TTS.

    Gera audio a partir de texto, com truncamento automatico,
    cache em memoria e fallback transparente.
    """

    def __init__(self, api_key: str, deepgram_service=None, audio_cache: AudioCache = None):
        self.api_key = api_key
        self.deepgram = deepgram_service  # fallback TTS
        self.cache = audio_cache or AudioCache()
        self._client: Optional[ElevenLabsClient] = None
        self.monthly_chars_used = 0
        self.max_chars = MAX_CHARS
        self.max_text_chars = 100  # truncar texto para no maximo 100 caracteres

    def _get_client(self) -> ElevenLabsClient:
        """Retorna (ou cria) o cliente ElevenLabs."""
        if self._client is None:
            self._client = ElevenLabsClient(api_key=self.api_key)
        return self._client

    def _truncate_text(self, text: str, max_chars: int = 100) -> str:
        """Trunca o texto para no maximo max_chars caracteres,
        mantendo a frase completa (corta no ultimo ponto antes do limite)."""
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]

        # Tenta cortar no ultimo ponto final
        last_period = truncated.rfind(".")
        if last_period > max_chars // 2:
            return truncated[: last_period + 1].strip()

        # Se nao achou ponto, corta no ultimo espaco
        last_space = truncated.rfind(" ")
        if last_space > max_chars // 2:
            return truncated[:last_space].strip() + "."

        return truncated.strip() + "."

    def get_usage_warning(self) -> str:
        """Retorna aviso de uso se estiver acima de 70%."""
        pct = (self.monthly_chars_used / self.max_chars) * 100
        if pct >= 90:
            remaining = self.max_chars - self.monthly_chars_used
            return (
                f"\n\n⚠️ *Almost out of audio!* "
                f"Only {remaining} characters remaining this month."
            )
        elif pct >= 70:
            return (
                f"\n\n💡 *Audio usage:* "
                f"{self.monthly_chars_used}/{self.max_chars} chars this month"
            )
        return ""

    async def generate_speech(self, text: str, voice_id: str = DEFAULT_VOICE_ID) -> Optional[bytes]:
        """Gera audio a partir do texto. Retorna bytes MP3 ou None.

        Args:
            text: Texto a ser convertido em audio (sera truncado para 100 chars).
            voice_id: ID da voz ElevenLabs (padrao: Rachel).

        Fluxo:
          1. Trunca texto para 100 chars
          2. Verifica cache (hash do texto + voice_id)
          3. Se ElevenLabs tem cota: usa ElevenLabs
          4. Se ElevenLabs excedeu: usa Deepgram TTS (fallback)
          5. Se ambos falharam: retorna None (resposta so texto)
        """
        # 1. Trunca texto
        truncated = self._truncate_text(text, max_chars=self.max_text_chars)

        # 2. Verifica cache (inclui voice_id na chave)
        cache_key = f"{voice_id}:{truncated}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # 3. Tenta ElevenLabs
        if self.monthly_chars_used < self.max_chars:
            audio = await self._try_elevenlabs(truncated, voice_id=voice_id)
            if audio is not None:
                self.cache.set(cache_key, audio)
                return audio

        # 4. Fallback: Deepgram TTS (ignora voice_id, Deepgram tem vozes fixas)
        if self.deepgram:
            logger.info("Usando Deepgram TTS como fallback para: %s", truncated[:50])
            audio = await self.deepgram.generate_speech(truncated)
            if audio is not None:
                self.cache.set(cache_key, audio)
                return audio

        # 5. Ambos falharam
        logger.error("TTS falhou: ElevenLabs e Deepgram ambos indisponiveis")
        return None

    async def _try_elevenlabs(self, text: str, voice_id: str = DEFAULT_VOICE_ID) -> Optional[bytes]:
        """Tenta gerar audio com ElevenLabs."""
        try:
            client = self._get_client()
            chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
            )

            audio_bytes = b"".join(chunks)
            if audio_bytes:
                self.monthly_chars_used += len(text)
                return audio_bytes

            logger.warning("ElevenLabs retornou audio vazio (voice: %s)", voice_id)
            return None

        except Exception as e:
            logger.error("Erro ao gerar audio com ElevenLabs (voice: %s): %s", voice_id, e)
            return None
