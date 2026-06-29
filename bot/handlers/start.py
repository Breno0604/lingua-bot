"""
LinguaBot --- Start Handler
Mensagem de boas-vindas com menu inicial e escolha de nivel.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.level_manager import LevelManager
from bot.utils.db_helpers import load_audio_prefs_from_db
from bot.utils.formatting import get_level_choice_text, get_welcome_text
from bot.utils.keyboards import level_selection_keyboard, main_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command. Shows welcome message and level selection.

    Antes de exibir o menu, carrega as preferencias do usuario
    (nivel, voz, velocidade) do banco para os caches, evitando
    chamadas ao banco na primeira mensagem ou acao.
    """
    user = update.effective_user
    first_name = user.first_name if user else "there"
    user_id = update.effective_user.id

    # Carrega preferencias do banco para os caches
    level_mgr: LevelManager = context.bot_data.get("level_manager")
    if level_mgr:
        await level_mgr.load_level(user_id)
    await load_audio_prefs_from_db(context, user_id)

    if level_mgr and not level_mgr.has_level(user_id):
        # Primeira vez (ou nunca escolheu nivel): mostra escolha
        welcome_text = get_welcome_text(first_name)
        await update.message.reply_text(
            welcome_text,
            reply_markup=level_selection_keyboard(),
            parse_mode="Markdown",
        )
    else:
        # Ja tem nivel: mostra menu principal COMPRIMIDO
        welcome_text = get_level_choice_text(first_name)
        context.user_data["screen_type"] = "menu"
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu(expanded=False),
            parse_mode="Markdown",
        )
