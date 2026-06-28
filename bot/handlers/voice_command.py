"""
LinguaBot --- Voice Command Handler

Comando /voice:
  - Mostra a voz atual do usuario (Deepgram Aura)
  - Oferece botoes para trocar de voz (Thalia, Odysseus, Helena, Mars)
  - Confirma a mudanca e aplica nas proximas respostas de audio
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.deepgram_tts import VOICE_MAP, DEFAULT_VOICE_ID
from bot.utils.keyboards import DEFAULT_SPEED_BY_LEVEL, voice_selection_keyboard

logger = logging.getLogger(__name__)


async def _load_audio_prefs_from_db(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Carrega voice_id e tts_speed do banco para user_data se nao estiverem em cache."""
    if "voice_id" in context.user_data and "tts_speed" in context.user_data:
        return  # Ja carregados
    db: BaseDatabase = context.bot_data.get("db")
    if not db:
        return
    try:
        prefs = await db.get_user_preferences(user_id)
        if "voice_id" not in context.user_data and prefs.voice_id:
            context.user_data["voice_id"] = prefs.voice_id
        if "tts_speed" not in context.user_data and prefs.tts_speed is not None:
            context.user_data["tts_speed"] = prefs.tts_speed
    except Exception as e:
        logger.warning("Erro ao carregar preferencias de audio: %s", e)


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /voice command. Shows current voice and selection menu."""
    deepgram_tts = context.bot_data.get("deepgram_tts")

    if not deepgram_tts:
        await update.message.reply_text(
            "Sorry, audio services aren't configured yet. "
            "Please set up DEEPGRAM_API_KEY in your .env file. \U0001f3b6"
        )
        return

    user_id = update.effective_user.id

    # Carrega preferencias do banco se necessario
    await _load_audio_prefs_from_db(context, user_id)

    current_voice_id = context.user_data.get("voice_id", DEFAULT_VOICE_ID)
    current_name, current_desc = VOICE_MAP.get(current_voice_id, ("Unknown", ""))

    # Resolve velocidade padrao baseada no nivel se nao foi personalizada
    level_mgr = context.bot_data.get("level_manager")
    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"
    default_speed = DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0)
    current_speed = context.user_data.get("tts_speed", default_speed)

    speed_labels = {
        0.75: "\U0001f422 Very slow",
        0.85: "Slow",
        1.0: "Normal",
        1.15: "Fast",
        1.25: "\U0001f407 Very fast",
    }

    text = (
        f"\U0001f50a **Current Voice:** {current_name}\n"
        f"_{current_desc}_\n\n"
        "Choose a different voice for my audio responses!\n"
        "All voices use Deepgram Aura \u2014 clear, calm, and natural.\n\n"
        f"\U0001f3a7 **Speaking Speed:** {current_speed}x ({speed_labels.get(current_speed, '')})"
    )

    await update.message.reply_text(
        text,
        reply_markup=voice_selection_keyboard(current_voice_id, current_speed),
        parse_mode="Markdown",
    )
