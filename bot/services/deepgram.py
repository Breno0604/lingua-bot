"""
LinguaBot --- Deepgram STT Client

Transcreve audio do usuario para texto usando Deepgram STT.
"""

from __future__ import annotations

import logging

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)


class DeepgramService:
    """Cliente Deepgram para STT (transcricao de audio)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: DeepgramClient | None = None

    def _get_client(self) -> DeepgramClient:
        if self._client is None:
            self._client = DeepgramClient(api_key=self.api_key)
        return self._client

    async def transcribe_audio(self, audio_bytes: bytes) -> str | None:
        """Transcreve audio do usuario usando Deepgram STT (nova-2)."""
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
