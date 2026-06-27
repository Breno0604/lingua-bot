"""
LinguaBot --- Deepgram Client

Dois modos:
  1. STT (pre-recorded): Transcreve audio do usuario para texto
  2. TTS (fallback): Gera audio quando ElevenLabs esta indisponivel
"""

import logging
from typing import Optional

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)


class DeepgramService:
    """Cliente Deepgram para STT (primario) e TTS (fallback)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[DeepgramClient] = None

    def _get_client(self) -> DeepgramClient:
        """Retorna (ou cria) o cliente Deepgram."""
        if self._client is None:
            self._client = DeepgramClient(api_key=self.api_key)
        return self._client

    async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """Transcreve audio do usuario usando Deepgram STT (nova-2).

        Args:
            audio_bytes: Conteudo do arquivo de audio (mp3/ogg/wav).

        Returns:
            Texto transcrito, ou None se falhou.
        """
        try:
            client = self._get_client()
            response = client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-2",
                language="en",
                punctuate=True,
                smart_format=True,
            )

            if response and response.results and response.results.channels:
                channel = response.results.channels[0]
                if channel.alternatives:
                    transcript = channel.alternatives[0].transcript
                    if transcript and transcript.strip():
                        return transcript.strip()

            logger.warning("Deepgram STT retornou transcricao vazia")
            return None

        except Exception as e:
            logger.error("Erro ao transcrever audio com Deepgram: %s", e)
            return None

    async def generate_speech(self, text: str) -> Optional[bytes]:
        """Gera audio TTS via Deepgram (modelo aura-asteria-en).

        Usado como FALLBACK quando ElevenLabs excede o limite mensal.

        Args:
            text: Texto a ser convertido em audio (max 100 chars).

        Returns:
            Bytes do audio MP3, ou None se falhou.
        """
        try:
            client = self._get_client()
            chunks = client.speak.v1.audio.generate(
                text=text,
                model="aura-asteria-en",
                encoding="mp3",
                container="none",
            )

            audio_bytes = b"".join(chunks)
            if audio_bytes:
                return audio_bytes

            logger.warning("Deepgram TTS retornou audio vazio")
            return None

        except Exception as e:
            logger.error("Erro ao gerar audio com Deepgram TTS: %s", e)
            return None
