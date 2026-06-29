"""
LinguaBot --- Start Handler
Mensagem de boas-vindas com menu inicial e escolha de nivel.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.voice_command import _load_audio_prefs_from_db
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
    await _load_audio_prefs_from_db(context, user_id)

    if level_mgr and not level_mgr.has_level(user_id):
        # Primeira vez (ou nunca escolheu nivel): mostra escolha
        welcome_text = _get_welcome_text(first_name)
        await update.message.reply_text(
            welcome_text,
            reply_markup=level_selection_keyboard(),
            parse_mode="Markdown",
        )
    else:
        # Ja tem nivel: mostra menu principal COMPRIMIDO
        welcome_text = _get_level_choice_text(first_name)
        context.user_data["screen_type"] = "menu"
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu(expanded=False),
            parse_mode="Markdown",
        )
