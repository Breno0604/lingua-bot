"""
LinguaBot --- Keyboards

Menus e botoes inline usados nos handlers.
Centraliza a definicao dos teclados para facilitar manutencao.

Todos os teclados agora suportam compressao via collapse_keyboard:
- expanded=False (padrao): mostra apenas "\u2795 More Options"
- expanded=True: mostra todos os botoes + "\u25c0 Hide Options"
"""

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Opcoes de velocidade de audio disponiveis
SPEED_OPTIONS = [0.75, 0.85, 1.0, 1.15, 1.25]

# Velocidade padrao por nivel de proficiencia
DEFAULT_SPEED_BY_LEVEL = {
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
}

# Botoes de controle de compressao
MORE_BUTTON = InlineKeyboardButton("\u2795 More Options", callback_data="show_more_options")
CONFIG_BUTTON = InlineKeyboardButton("\u2699\ufe0f Configuration", callback_data="show_config")
HIDE_BUTTON = InlineKeyboardButton("\u25c0 Hide Options", callback_data="hide_options")


def collapse_keyboard(
    expanded_keyboard: list[list[InlineKeyboardButton]],
    expanded: bool = False,
) -> InlineKeyboardMarkup:
    """Encapsula um teclado inline com comportamento de expandir/recolher."""
    if expanded:
        keyboard = list(expanded_keyboard)
        keyboard.append([HIDE_BUTTON])
        return InlineKeyboardMarkup(keyboard)

    return InlineKeyboardMarkup([[MORE_BUTTON]])


def main_menu(expanded: bool = False) -> InlineKeyboardMarkup:
    """Menu principal exibido no /start."""
    keyboard = [
        [
            InlineKeyboardButton("\U0001f4ac Start a Conversation", callback_data="start_conversation"),
            InlineKeyboardButton("\u2753 How it Works", callback_data="how_it_works"),
        ],
        [
            InlineKeyboardButton("\U0001f4da My Vocabulary", callback_data="show_vocab"),
            InlineKeyboardButton("\U0001f3af Practice Topics", callback_data="show_topics"),
        ],
    ]
    return collapse_keyboard(keyboard, expanded=expanded)


def conversation_buttons(expanded: bool = False) -> InlineKeyboardMarkup:
    """Botoes exibidos apos cada resposta do bot."""
    if expanded:
        keyboard = [
            [
                InlineKeyboardButton("\U0001f4dd Example", callback_data="more_examples"),
                InlineKeyboardButton("\U0001f4d6 Explain", callback_data="explain_word"),
                InlineKeyboardButton("\U0001f3af Practice", callback_data="practice_this"),
            ],
            [HIDE_BUTTON],
        ]
        return InlineKeyboardMarkup(keyboard)
    return InlineKeyboardMarkup([[MORE_BUTTON, CONFIG_BUTTON]])


def vocab_pagination(page: int, total_pages: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """Botoes de paginacao para a lista de vocabulario."""
    keyboard = []

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("\u25c0\ufe0f Previous", callback_data=f"vocab_page_{page - 1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next \u25b6\ufe0f", callback_data=f"vocab_page_{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")])
    return collapse_keyboard(keyboard, expanded=expanded)


def topic_suggestion(topic: str) -> InlineKeyboardMarkup:
    """Botoes apos sugestao de topico. SEM compressao — sempre visivel."""
    keyboard = [
        [
            InlineKeyboardButton("\u2705 Yes, let's talk!", callback_data=f"start_topic_{topic}"),
            InlineKeyboardButton("\U0001f504 Another Topic", callback_data="show_topics"),
        ],
        [InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def topics_menu(expanded: bool = False) -> InlineKeyboardMarkup:
    """Menu com a lista de topicos disponiveis (primeiros 5)."""
    keyboard = [
        [
            InlineKeyboardButton("\U0001f44b Greetings", callback_data="start_topic_Greetings"),
            InlineKeyboardButton("\U0001f354 Food & Drinks", callback_data="start_topic_Food & Drinks"),
        ],
        [
            InlineKeyboardButton("\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466 Family", callback_data="start_topic_Family"),
            InlineKeyboardButton("\u26c5 Weather", callback_data="start_topic_Weather"),
        ],
        [
            InlineKeyboardButton("\U0001f4c5 Daily Routine", callback_data="start_topic_Daily Routine"),
        ],
        [
            InlineKeyboardButton("\U0001f3b2 Random Topic", callback_data="show_topics"),
        ],
        [InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")],
    ]
    return collapse_keyboard(keyboard, expanded=expanded)


def level_selection_keyboard(current_level: str = "A1") -> InlineKeyboardMarkup:
    """Botoes para escolha de nivel de ingles. SEM compressao — sempre visivel."""
    from bot.services.level_manager import LevelManager

    keyboard = []
    for level in LevelManager.VALID_LEVELS:
        label = LevelManager.LEVEL_LABELS[level]
        if level == current_level:
            label = f"\u2705 {label}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_level_{level}")])
    return InlineKeyboardMarkup(keyboard)


def voice_selection_keyboard(current_voice_id: str, current_speed: float = 1.0) -> InlineKeyboardMarkup:
    """Botoes para escolha de voz (Deepgram Aura) + velocidade.

    Inclui 5 opcoes de velocidade (0.75 a 1.25).
    SEM compressao — sempre visivel.
    """
    from bot.services.deepgram_tts import VOICES

    keyboard = []
    # Secao de vozes
    for vid, name, desc in VOICES:
        label = f"\U0001f50a {name}" if vid == current_voice_id else f"{name}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_voice_{vid}")])

    # Secao de velocidade
    speed_row = []
    for speed_val in SPEED_OPTIONS:
        emoji = ""
        if speed_val == 0.75:
            emoji = "\U0001f422 "  # turtle
        elif speed_val == 1.25:
            emoji = "\U0001f407 "   # rabbit
        marker = " \u25cf" if speed_val == current_speed else ""
        label = f"{emoji}{speed_val}x{marker}"
        speed_row.append(InlineKeyboardButton(label, callback_data=f"set_speed_{speed_val}"))
    keyboard.append(speed_row)

    keyboard.append([InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def config_menu_keyboard() -> InlineKeyboardMarkup:
    """Botoes do menu de configuracao: Voice e Level."""
    keyboard = [
        [
            InlineKeyboardButton("\U0001f3a4 Voice", callback_data="show_voice_picker"),
            InlineKeyboardButton("\U0001f4ca Level", callback_data="show_level_picker"),
        ],
        [HIDE_BUTTON],
    ]
    return InlineKeyboardMarkup(keyboard)


def voice_picker_keyboard(current_voice_id: str, current_speed: float = 1.0) -> InlineKeyboardMarkup:
    """Botoes para escolha de voz + velocidade (dentro do config)."""
    from bot.services.deepgram_tts import VOICES

    keyboard = []
    for vid, name, desc in VOICES:
        label = f"\U0001f50a {name}" if vid == current_voice_id else f"{name}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_voice_{vid}")])

    speed_row = []
    for speed_val in SPEED_OPTIONS:
        emoji = "\U0001f422 " if speed_val == 0.75 else ("\U0001f407 " if speed_val == 1.25 else "")
        marker = " \u25cf" if speed_val == current_speed else ""
        speed_row.append(InlineKeyboardButton(f"{emoji}{speed_val}x{marker}", callback_data=f"set_speed_{speed_val}"))
    keyboard.append(speed_row)

    keyboard.append([HIDE_BUTTON])
    return InlineKeyboardMarkup(keyboard)


def level_picker_keyboard(current_level: str = "A1") -> InlineKeyboardMarkup:
    """Botoes para escolha de nivel (dentro do config)."""
    from bot.services.level_manager import LevelManager

    keyboard = []
    for level in LevelManager.VALID_LEVELS:
        label = LevelManager.LEVEL_LABELS[level]
        if level == current_level:
            label = f"\u2705 {label}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_level_{level}")])
    keyboard.append([HIDE_BUTTON])
    return InlineKeyboardMarkup(keyboard)


async def cleanup_old_buttons(context, chat_id: int) -> None:
    """Remove botoes de acao de todas as mensagens do bot rastreadas."""
    msg_ids = context.user_data.get("button_msg_ids", [])
    if not msg_ids:
        return
    for msg_id in list(msg_ids):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=msg_id, reply_markup=None
            )
            await asyncio.sleep(0.05)
        except Exception:
            pass
    context.user_data["button_msg_ids"] = []


def back_to_menu_button() -> InlineKeyboardMarkup:
    """Botao simples de voltar ao menu. SEM compressao — ja e um unico botao."""
    keyboard = [[InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)
