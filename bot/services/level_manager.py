"""
LinguaBot --- Level Manager

Gerencia o nivel de proficiencia de cada usuario.
Suporta A1, A2, B1 com labels e mensagens de confirmacao.

O nivel e sincronizado com o banco de dados (SQLite / Supabase)
quando disponivel, permitindo persistencia entre restarts.

Se nao houver banco configurado, funciona apenas em RAM (fallback).
"""

from __future__ import annotations

from bot.database import BaseDatabase


class LevelManager:
    """Gerencia o nivel de proficiencia de cada usuario com persistencia."""

    VALID_LEVELS = ["A1", "A2", "B1"]

    LEVEL_LABELS = {
        "A1": "A1 - Iniciante",
        "A2": "A2 - B\u00e1sico",
        "B1": "B1 - Intermedi\u00e1rio",
    }

    LEVEL_CONFIRMATIONS = {
        "A1": (
            "I'll use very simple words and short sentences. "
            "Let's start practicing! \U0001f680"
        ),
        "A2": (
            "I'll use everyday vocabulary and slightly longer sentences now. "
            "You're doing great! \U0001f31f"
        ),
        "B1": (
            "I'll use more varied vocabulary and natural expressions. "
            "Let's have a real conversation! \U0001f44d"
        ),
    }

    def __init__(self, default_level: str = "A1", db: BaseDatabase | None = None):
        self.default_level = default_level
        self.db = db
        # Cache em memoria (evita ler do banco a cada chamada)
        self._levels: dict[int, str] = {}

    async def load_level(self, user_id: int) -> str:
        """Carrega o nivel do banco e atualiza o cache.

        Retorna o nivel persistido, ou default se nao existir.
        """
        if self.db:
            try:
                prefs = await self.db.get_user_preferences(user_id)
                if prefs.level:
                    self._levels[user_id] = prefs.level
                    return prefs.level
            except Exception as e:
                __import__("logging").getLogger(__name__).warning(
                    "Erro ao carregar nivel do banco: %s", e
                )
        return self.get_level(user_id)

    def get_level(self, user_id: int) -> str:
        """Retorna o nivel do usuario (cache primeiro, depois default)."""
        return self._levels.get(user_id, self.default_level)

    async def set_level(self, user_id: int, level: str) -> bool:
        """Define o nivel do usuario e persiste no banco.

        Returns:
            False se nivel invalido, True se sucesso.
        """
        if level not in self.VALID_LEVELS:
            return False
        self._levels[user_id] = level
        if self.db:
            try:
                await self.db.set_user_preferences(user_id, level=level)
            except Exception as e:
                __import__("logging").getLogger(__name__).error(
                    "Erro ao persistir nivel para user %d: %s", user_id, e
                )
        return True

    def get_label(self, level: str) -> str:
        """Retorna o label amigavel para um nivel."""
        return self.LEVEL_LABELS.get(level, level)

    def get_confirmation(self, level: str) -> str:
        """Retorna a mensagem de confirmacao para um nivel."""
        return self.LEVEL_CONFIRMATIONS.get(level, "")

    def remove(self, user_id: int) -> None:
        """Remove o nivel de um usuario (volta ao default)."""
        self._levels.pop(user_id, None)

    def has_level(self, user_id: int) -> bool:
        """Verifica se o usuario ja definiu um nivel explicitamente (em cache)."""
        return user_id in self._levels
