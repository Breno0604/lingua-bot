"""
LinguaBot --- Start Handler
Mensagem de boas-vindas com menu inicial e escolha de nivel.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.level_manager import LevelManager
from bot.utils.keyboards import level_selection_keyboard, main_menu


def _get_welcome_text(first_name: str) -> str:
    """Retorna o texto de boas-vindas."""
    return (
        f"\U0001f44b Hello {first_name}! I'm **LinguaBot**, your English teacher! \U0001f389\n\n"
        "I'm here to help you practice English. We can talk about many topics, "
        "and I'll gently correct your mistakes along the way.\n\n"
        "**First, let's set your English level** so I can adapt to you!"
    )


def _get_level_choice_text(first_name: str) -> str:
    """Texto para escolha de nivel."""
    return (
        f"\U0001f44b Hello {first_name}! I'm **LinguaBot**, your English teacher! \U0001f389\n\n"
        "I'm here to help you practice English.\n\n"
        "**Great! Let's start practicing!** \U0001f680\n\n"
        "You can change your level anytime with /level"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command. Shows welcome message and level selection."""
    user = update.effective_user
    first_name = user.first_name if user else "there"

    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if level_mgr and not level_mgr.has_level(update.effective_user.id):
        # Primeira vez: mostra escolha de nivel
        welcome_text = _get_welcome_text(first_name)
        await update.message.reply_text(
            welcome_text,
            reply_markup=level_selection_keyboard(),
            parse_mode="Markdown",
        )
    else:
        # Ja tem nivel: mostra menu normal
        welcome_text = _get_level_choice_text(first_name)
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
