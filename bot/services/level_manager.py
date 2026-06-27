"""
LinguaBot --- Level Manager

Gerencia o nivel de proficiencia de cada usuario em memoria.
Suporta A1, A2, B1 com labels e mensagens de confirmacao.

O nivel e armazenado apenas em RAM. Se o bot reiniciar,
o usuario volta para A1 (default) e precisa redefinir via /level.
"""

from typing import Dict, Optional


class LevelManager:
    """Gerencia o nivel de proficiencia de cada usuario em memoria."""

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

    def __init__(self, default_level: str = "A1"):
        self.default_level = default_level
        self._levels: Dict[int, str] = {}

    def get_level(self, user_id: int) -> str:
        """Retorna o nivel do usuario (default: A1 se nunca definiu)."""
        return self._levels.get(user_id, self.default_level)

    def set_level(self, user_id: int, level: str) -> bool:
        """Define o nivel do usuario. Retorna False se nivel invalido."""
        if level not in self.VALID_LEVELS:
            return False
        self._levels[user_id] = level
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
        """Verifica se o usuario ja definiu um nivel explicitamente."""
        return user_id in self._levels
