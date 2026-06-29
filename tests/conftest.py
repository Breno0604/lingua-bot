"""
LinguaBot --- Shared Test Fixtures

Fixtures e mocks compartilhados entre todos os testes.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Garante que a raiz do projeto esta no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from bot.database import VocabEntry


@pytest.fixture
def mock_tts_orchestrator():
    """Mock do TTSOrchestrator — retorna audio com sucesso."""
    tts = MagicMock()
    tts.generate_audio = AsyncMock(return_value=b"fake_tts_audio")
    return tts


@pytest.fixture
def mock_update():
    """Cria um mock de Update do Telegram com suporte a await."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.first_name = "TestUser"
    update.effective_chat.id = 12345

    # message mock com suporte a async
    msg = MagicMock()
    msg.text = "Hello! How are you?"
    msg.chat.send_action = AsyncMock()
    msg.reply_text = AsyncMock()
    update.message = msg

    # callback_query mock com suporte a async
    cq = MagicMock()
    cq.answer = AsyncMock()
    cq.edit_message_text = AsyncMock()
    cq.from_user.id = 12345
    cq.message = MagicMock()
    cq.message.voice = None  # nao e mensagem de voz por padrao
    cq.message.reply_text = AsyncMock()
    update.callback_query = cq

    return update


@pytest.fixture
def mock_context():
    """Cria um mock de ContextTypes.DEFAULT_TYPE com bot_data."""
    context = MagicMock()
    context.bot_data = {}
    return context


@pytest.fixture
def mock_db():
    """Cria um mock do banco de dados."""
    db = MagicMock()
    db.save_vocab = AsyncMock()
    db.get_vocab = AsyncMock(return_value=[])
    db.get_vocab_count = AsyncMock(return_value=0)
    db.practice_word = AsyncMock()
    db.get_user_preferences = AsyncMock(return_value=None)
    db.set_user_preferences = AsyncMock()
    return db


@pytest.fixture
def mock_groq():
    """Cria um mock do GroqService."""
    groq = MagicMock()
    groq.generate_reply = AsyncMock(return_value="Hello! How are you today? 😊")
    return groq


@pytest.fixture
def mock_conversation_mgr():
    """Cria um mock do ConversationManager com contexto funcional."""
    from bot.services.conversation import ConversationContext

    actual_ctx = ConversationContext(max_turns=15)

    mgr = MagicMock()
    mgr.get_or_create = MagicMock(return_value=actual_ctx)
    mgr.reset = MagicMock(side_effect=lambda uid: actual_ctx.clear())
    mgr.remove = MagicMock()
    mgr.active_users = 0
    return mgr


@pytest.fixture
def mock_rate_limiter():
    """Cria um mock do RateLimiter."""
    rl = MagicMock()
    rl.check_and_increment = MagicMock(return_value={
        "allowed": True,
        "current": 1,
        "limit": 100,
        "remaining": 99,
        "warning": None,
    })
    rl.get_status = MagicMock(return_value={
        "current": 5,
        "limit": 100,
        "remaining": 95,
    })
    rl.reset_user = MagicMock()
    return rl


@pytest.fixture
def configured_context(mock_context, mock_db, mock_groq, mock_conversation_mgr, mock_rate_limiter):
    """Context pre-configurado com todos os servicos."""
    mock_context.bot_data["db"] = mock_db
    mock_context.bot_data["groq"] = mock_groq
    mock_context.bot_data["conversation_mgr"] = mock_conversation_mgr
    mock_context.bot_data["rate_limiter"] = mock_rate_limiter
    return mock_context


@pytest.fixture
def sample_vocab_entries():
    """Retorna algumas entradas de vocabulario de exemplo."""
    return [
        VocabEntry(
            id=1, user_id=12345, word="breakfast",
            translation="cafe da manha", context="I eat breakfast at 7am.",
            created_at="2026-06-26 10:00:00", reviewed_at=None, practice_count=3,
        ),
        VocabEntry(
            id=2, user_id=12345, word="weather",
            translation="clima / tempo", context="The weather is sunny today.",
            created_at="2026-06-26 09:00:00", reviewed_at=None, practice_count=1,
        ),
        VocabEntry(
            id=3, user_id=12345, word="dog",
            translation="cachorro", context="I have a dog.",
            created_at="2026-06-25 15:00:00", reviewed_at=None, practice_count=0,
        ),
    ]
