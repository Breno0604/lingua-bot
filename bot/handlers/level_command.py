"""
LinguaBot --- Level Command Handler

Comando /level:
  - Mostra o nivel atual do usuario
  - Oferece 3 botoes para trocar de nivel (A1, A2, B1)
  - Confirma a mudanca e informa como a resposta sera adaptada
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.level_manager import LevelManager
from bot.utils.keyboards import level_selection_keyboard

logger = logging.getLogger(__name__)


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /level command. Shows current level and selection menu."""
    user_id = update.effective_user.id
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not level_mgr:
        await update.message.reply_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f"
        )
        return

    current = level_mgr.get_level(user_id)
    label = level_mgr.get_label(current)

    text = (
        f"\U0001f4ca **Your English Level**\n\n"
        f"Current level: **{label}**\n\n"
        "Choose your level below. I'll adapt my responses "
        "to match your English skills!"
    )

    await update.message.reply_text(
        text,
        reply_markup=level_selection_keyboard(current),
        parse_mode="Markdown",
    )
