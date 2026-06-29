"""
Tests para bot.handlers.commands

Testa os comandos /reset, /vocab e /topic com mocks do Telegram.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.commands import reset_command, vocab_command, topic_command


class TestResetCommand:
    """Testes para /reset."""

    @pytest.mark.asyncio
    async def test_reset_success(self, mock_update, configured_context):
        """/reset limpa historico e sugere topico."""
        mock_update.message.text = "/reset"
        await reset_command(mock_update, configured_context)

        # Verifica que chamou reset
        configured_context.bot_data["conversation_mgr"].reset.assert_called_once_with(12345)

        # Verifica que enviou mensagem de confirmacao
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[0][0]
        assert "reset" in text.lower()
        assert "Conversation" in text
        assert "topic" in text.lower()

    @pytest.mark.asyncio
    async def test_reset_no_conversation_mgr(self, mock_update, mock_context):
        """/reset sem conversation_mgr mostra erro."""
        mock_context.bot_data["conversation_mgr"] = None
        mock_update.message.text = "/reset"
        await reset_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "not ready" in text.lower()


class TestVocabCommand:
    """Testes para /vocab."""

    @pytest.mark.asyncio
    async def test_vocab_empty(self, mock_update, configured_context):
        """/vocab com lista vazia mostra mensagem apropriada."""
        configured_context.bot_data["db"].get_vocab_count = AsyncMock(return_value=0)
        configured_context.bot_data["db"].get_vocab = AsyncMock(return_value=[])

        mock_update.message.text = "/vocab"
        await vocab_command(mock_update, configured_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "don't have any words" in text.lower()

    @pytest.mark.asyncio
    async def test_vocab_with_entries(self, mock_update, configured_context, sample_vocab_entries):
        """/vocab com entradas mostra lista formatada."""
        configured_context.bot_data["db"].get_vocab_count = AsyncMock(return_value=3)
        configured_context.bot_data["db"].get_vocab = AsyncMock(return_value=sample_vocab_entries)

        mock_update.message.text = "/vocab"
        await vocab_command(mock_update, configured_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "breakfast" in text
        assert "weather" in text
        assert "dog" in text
        assert "3 words" in text

    @pytest.mark.asyncio
    async def test_vocab_no_db(self, mock_update, mock_context):
        """/vocab sem db mostra erro."""
        mock_context.bot_data["db"] = None
        mock_update.message.text = "/vocab"
        await vocab_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "not ready" in text.lower()

    @pytest.mark.asyncio
    async def test_vocab_db_error(self, mock_update, configured_context):
        """/vocab com erro no banco mostra mensagem de erro."""
        configured_context.bot_data["db"].get_vocab_count = AsyncMock(side_effect=Exception("DB error"))

        mock_update.message.text = "/vocab"
        await vocab_command(mock_update, configured_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "sorry" in text.lower()


class TestTopicCommand:
    """Testes para /topic."""

    @pytest.mark.asyncio
    async def test_topic_suggestion(self, mock_update, mock_context):
        """/topic sugere um topico valido."""
        mock_update.message.text = "/topic"
        await topic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[0][0]
        assert "topic" in text.lower()
        assert "practice" in text.lower()
        assert "Let's" in text

    @pytest.mark.asyncio
    async def test_topic_different_each_time(self, mock_update, mock_context):
        """/topic pode sugerir topicos diferentes (teste estatistico)."""
        topics_seen = set()
        for _ in range(30):
            mock_update.message.reply_text = AsyncMock()
            await topic_command(mock_update, mock_context)
            text = mock_update.message.reply_text.call_args[0][0]
            # Extrai o nome do topico do texto
            for t_name in ["Greetings", "Food", "Family", "Weather", "Daily Routine"]:
                if t_name in text:
                    topics_seen.add(t_name)
                    break

        # Em 30 tentativas, deve ter visto pelo menos 3 topicos diferentes
        assert len(topics_seen) >= 3, f"Sugeriu sempre os mesmos topicos? {topics_seen}"
