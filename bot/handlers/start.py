"""
LinguaBot --- Start Handler
Mensagem de boas-vindas com menu inicial e sugestao de topico.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.keyboards import main_menu


def _get_welcome_text(first_name: str) -> str:
    """Retorna o texto de boas-vindas."""
    return (
        f"👋 Hello {first_name}! I'm **LinguaBot**, your English teacher! 🎉\n\n"
        "I'm here to help you practice English. We can talk about many topics, "
        "and I'll gently correct your mistakes along the way.\n\n"
        "Let's start learning together! 🚀"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command. Shows welcome message and menu."""
    user = update.effective_user
    first_name = user.first_name if user else "there"

    welcome_text = _get_welcome_text(first_name)

    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )
