"""
LinguaBot --- Conversation Context Manager

Mantem o historico da conversa para cada usuario (10-15 mensagens).
O contexto e armazenado em memoria (dicionario) e nao persiste entre restarts.
"""

from __future__ import annotations

from collections import deque


class ConversationContext:
    """Gerencia o contexto da conversa para um unico usuario."""

    def __init__(self, max_turns: int = 15):
        self.max_turns = max_turns
        # Cada entrada: (role, message) onde role="user" ou "assistant"
        self._history: deque[tuple[str, str]] = deque(maxlen=max_turns)

    def add_user_message(self, text: str) -> None:
        """Adiciona uma mensagem do usuario ao historico."""
        self._history.append(("user", text))

    def add_assistant_message(self, text: str) -> None:
        """Adiciona uma resposta do bot ao historico."""
        self._history.append(("assistant", text))

    def get_history(self) -> list[tuple[str, str]]:
        """Retorna o historico completo como lista de (role, message)."""
        return list(self._history)

    def clear(self) -> None:
        """Limpa todo o historico da conversa."""
        self._history.clear()

    def get_formatted_history(self) -> str:
        """Retorna o historico formatado para incluir no prompt do Gemini."""
        lines = []
        for role, message in self._history:
            prefix = "Student" if role == "user" else "Teacher"
            lines.append(f"{prefix}: {message}")
        return "\n".join(lines)

    @property
    def turn_count(self) -> int:
        """Numero de trocas de mensagens no historico."""
        return len(self._history) // 2


class ConversationManager:
    """Gerencia contextos de conversa para multiplos usuarios."""

    def __init__(self, max_turns: int = 15):
        self.max_turns = max_turns
        self._contexts: dict[int, ConversationContext] = {}

    def get_or_create(self, user_id: int) -> ConversationContext:
        """Retorna o contexto existente ou cria um novo para o usuario."""
        if user_id not in self._contexts:
            self._contexts[user_id] = ConversationContext(self.max_turns)
        return self._contexts[user_id]

    def reset(self, user_id: int) -> None:
        """Reseta o contexto de um usuario."""
        if user_id in self._contexts:
            self._contexts[user_id].clear()

    @property
    def active_users(self) -> int:
        """Numero de usuarios com conversa ativa."""
        return len(self._contexts)
