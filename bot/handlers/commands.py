"""
LinguaBot --- Commands Handler

Comandos adicionais do bot:
  - /reset: Limpa o historico da conversa
  - /vocab: Mostra o vocabulario aprendido
  - /topic: Sugere um topico para praticar
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.utils.formatting import (
    format_topic_suggestion,
    format_vocab_list,
    get_random_topic,
    split_long_message,
)
from bot.utils.keyboards import (
    back_to_menu_button,
    topic_suggestion,
    vocab_pagination,
)

logger = logging.getLogger(__name__)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command. Clears conversation history."""
    user_id = update.effective_user.id
    conversation_mgr: ConversationManager = context.bot_data.get("conversation_mgr")

    if not conversation_mgr:
        await update.message.reply_text(
            "Sorry, I'm not ready yet. Please try /start again! 🙏"
        )
        return

    conversation_mgr.reset(user_id)

    # Sugere um topico apos o reset
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    text = (
        "🔄 **Conversation reset!**\n\n"
        "I've cleared our conversation history. "
        "Feel free to start a new topic!\n\n"
        f"{suggestion}"
    )

    await update.message.reply_text(
        text,
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )


async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /vocab command. Shows saved vocabulary filtered by user level."""
    user_id = update.effective_user.id
    db: BaseDatabase = context.bot_data.get("db")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not db:
        await update.message.reply_text(
            "Sorry, I'm not ready yet. Please try /start again! 🙏"
        )
        return

    # Filtra vocabulario pelo nivel atual do usuario
    user_level = level_mgr.get_level(user_id) if level_mgr else None

    page = 1
    page_size = 10

    try:
        total = await db.get_vocab_count(user_id, level=user_level)
        entries = await db.get_vocab(user_id, page=page, page_size=page_size, level=user_level)
    except Exception as e:
        logger.error("Erro ao buscar vocabulario: %s", e)
        await update.message.reply_text(
            "Sorry, I couldn't get your vocabulary right now. Please try again later! 🙏"
        )
        return

    text = format_vocab_list(entries, total, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)

    reply_markup = vocab_pagination(page, total_pages) if entries else back_to_menu_button()

    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /topic command. Suggests a random practice topic."""
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    await update.message.reply_text(
        suggestion,
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )
