"""
LinguaBot --- Voice Command Handler

Comando /voice:
  - Mostra a voz atual do usuario
  - Oferece botoes para trocar de voz (Rachel, Stephanie v2, Eryn, Leo v2, Jerry B.)
  - Confirma a mudanca e aplica nas proximas respostas de audio
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.elevenlabs import VOICE_MAP, DEFAULT_VOICE_ID
from bot.utils.keyboards import voice_selection_keyboard

logger = logging.getLogger(__name__)


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /voice command. Shows current voice and selection menu."""
    elevenlabs = context.bot_data.get("elevenlabs")

    if not elevenlabs:
        await update.message.reply_text(
            "Sorry, audio services aren't configured yet. "
            "Please set up ELEVENLABS_API_KEY in your .env file. \U0001f3b6"
        )
        return

    current_voice_id = context.user_data.get("voice_id", DEFAULT_VOICE_ID)
    current_name, current_desc = VOICE_MAP.get(current_voice_id, ("Unknown", ""))

    text = (
        f"\U0001f50a **Current Voice:** {current_name}\n"
        f"_{current_desc}_\n\n"
        "Choose a different voice for my audio responses!\n"
        "All voices speak English clearly."
    )

    await update.message.reply_text(
        text,
        reply_markup=voice_selection_keyboard(current_voice_id),
        parse_mode="Markdown",
    )
