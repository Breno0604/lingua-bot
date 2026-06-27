"""
LinguaBot --- Audio Cache

Cache em memoria de audios gerados (TTS).
Usa hash MD5 do texto como chave para evitar
regerar o mesmo audio multiplas vezes.

E um cache volatil — perdido ao restart do bot.
"""

import hashlib
from typing import Optional


class AudioCache:
    """Cache em memoria de audios gerados (hash do texto -> bytes)."""

    def __init__(self):
        self._cache: dict[str, bytes] = {}

    def _hash(self, text: str) -> str:
        """Gera hash MD5 do texto para usar como chave."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[bytes]:
        """Retorna audio em cache, ou None se nao existir."""
        key = self._hash(text)
        return self._cache.get(key)

    def set(self, text: str, audio: bytes) -> None:
        """Armazena audio no cache."""
        key = self._hash(text)
        self._cache[key] = audio

    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Numero de itens no cache."""
        return len(self._cache)
