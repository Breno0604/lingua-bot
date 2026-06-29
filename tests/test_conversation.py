"""
Tests para bot.services.conversation
"""

from __future__ import annotations

import pytest
from bot.services.conversation import ConversationContext, ConversationManager


class TestConversationContext:
    """Testes para ConversationContext."""

    def test_initial_state(self):
        """Contexto comeca vazio."""
        ctx = ConversationContext(max_turns=15)
        assert len(ctx.get_history()) == 0
        assert ctx.turn_count == 0

    def test_add_user_message(self):
        """Adicionar mensagem do usuario."""
        ctx = ConversationContext()
        ctx.add_user_message("Hello!")
        history = ctx.get_history()
        assert len(history) == 1
        assert history[0] == ("user", "Hello!")

    def test_add_assistant_message(self):
        """Adicionar resposta do bot."""
        ctx = ConversationContext()
        ctx.add_assistant_message("Hi there!")
        history = ctx.get_history()
        assert len(history) == 1
        assert history[0] == ("assistant", "Hi there!")

    def test_turn_count(self):
        """Turn count conta pares de mensagens."""
        ctx = ConversationContext()
        assert ctx.turn_count == 0

        ctx.add_user_message("Hello!")
        ctx.add_assistant_message("Hi!")
        assert ctx.turn_count == 1

        ctx.add_user_message("How are you?")
        ctx.add_assistant_message("I'm great!")
        assert ctx.turn_count == 2

    def test_clear(self):
        """Clear limpa todo o historico."""
        ctx = ConversationContext()
        ctx.add_user_message("Hello!")
        ctx.add_assistant_message("Hi!")
        ctx.clear()
        assert len(ctx.get_history()) == 0
        assert ctx.turn_count == 0

    def test_get_formatted_history(self):
        """Formatacao correta do historico."""
        ctx = ConversationContext()
        ctx.add_user_message("Hello!")
        ctx.add_assistant_message("Hi! How are you?")

        formatted = ctx.get_formatted_history()
        assert "Student: Hello!" in formatted
        assert "Teacher: Hi! How are you?" in formatted

    def test_max_turns_enforced(self):
        """Historico respeita o limite de turnos."""
        ctx = ConversationContext(max_turns=4)  # 4 entradas = 2 turnos
        ctx.add_user_message("1")
        ctx.add_assistant_message("A")
        ctx.add_user_message("2")
        ctx.add_assistant_message("B")
        ctx.add_user_message("3")  # Essa deve expulsar a primeira

        history = ctx.get_history()
        assert len(history) == 4  # maxlen mantem no maximo 4 entradas
        assert history[0] == ("assistant", "A")  # "1" foi removida
        assert history[-1] == ("user", "3")


class TestConversationManager:
    """Testes para ConversationManager."""

    def test_get_or_create_new(self):
        """Cria novo contexto para usuario inexistente."""
        mgr = ConversationManager()
        ctx = mgr.get_or_create(12345)
        assert isinstance(ctx, ConversationContext)
        assert ctx.turn_count == 0

    def test_get_or_create_existing(self):
        """Retorna o mesmo contexto para usuario existente."""
        mgr = ConversationManager()
        ctx1 = mgr.get_or_create(12345)
        ctx1.add_user_message("Hello!")

        ctx2 = mgr.get_or_create(12345)
        assert ctx1 is ctx2  # Mesmo objeto
        assert len(ctx2.get_history()) == 1  # Historico preservado

    def test_reset(self):
        """Reset limpa o historico do usuario."""
        mgr = ConversationManager()
        ctx = mgr.get_or_create(12345)
        ctx.add_user_message("Hello!")
        ctx.add_assistant_message("Hi!")

        mgr.reset(12345)
        assert len(ctx.get_history()) == 0

    def test_reset_nonexistent(self):
        """Reset em usuario inexistente nao causa erro."""
        mgr = ConversationManager()
        mgr.reset(99999)  # Nao deve levantar excecao

    def test_active_users(self):
        """active_users conta usuarios com contexto."""
        mgr = ConversationManager()
        assert mgr.active_users == 0

        mgr.get_or_create(1)
        mgr.get_or_create(2)
        mgr.get_or_create(3)
        assert mgr.active_users == 3

    def test_multiple_users_independent(self):
        """Contextos de usuarios diferentes sao independentes."""
        mgr = ConversationManager()
        ctx1 = mgr.get_or_create(1)
        ctx2 = mgr.get_or_create(2)

        ctx1.add_user_message("Hello from user 1")
        ctx2.add_user_message("Hello from user 2")

        assert len(ctx1.get_history()) == 1
        assert len(ctx2.get_history()) == 1
        assert ctx1.get_history()[0][1] == "Hello from user 1"
        assert ctx2.get_history()[0][1] == "Hello from user 2"
