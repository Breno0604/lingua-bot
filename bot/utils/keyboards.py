"""
LinguaBot --- Keyboards

Menus e botoes inline usados nos handlers.
Centraliza a definicao dos teclados para facilitar manutencao.

Todos os teclados agora suportam compressao via collapse_keyboard:
- expanded=False (padrao): mostra apenas "\u2795 More Options"
- expanded=True: mostra todos os botoes + "\u25c0 Hide Options"
"""

from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constants import DEFAULT_SPEED_BY_LEVEL, SPEED_OPTIONS

def _pad(text: str) -> str:
    """Adiciona 5 espacos nas bordas para aumentar a largura do botao."""
    return f"     {text}     "

# Botoes de controle de compressao
MORE_BUTTON = InlineKeyboardButton(_pad("\u2795 More Options"), callback_data="show_more_options")
CONFIG_BUTTON = InlineKeyboardButton(_pad("\u2699\ufe0f Configuration"), callback_data="show_config")
HIDE_BUTTON = InlineKeyboardButton(_pad("\u25c0 Hide Options"), callback_data="hide_options")


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
            InlineKeyboardButton(_pad("\U0001f4ac Start a Conversation"), callback_data="start_conversation"),
            InlineKeyboardButton(_pad("\u2753 How it Works"), callback_data="how_it_works"),
        ],
        [
            InlineKeyboardButton(_pad("\U0001f4da My Vocabulary"), callback_data="show_vocab"),
            InlineKeyboardButton(_pad("\U0001f3af Practice Topics"), callback_data="show_topics"),
        ],
    ]
    return collapse_keyboard(keyboard, expanded=expanded)


def conversation_buttons(expanded: bool = False) -> InlineKeyboardMarkup:
    """Botoes exibidos apos cada resposta do bot."""
    if expanded:
        keyboard = [
            [
                InlineKeyboardButton(_pad("\U0001f4dd Example"), callback_data="more_examples"),
                InlineKeyboardButton(_pad("\U0001f4d6 Explain"), callback_data="explain_word"),
                InlineKeyboardButton(_pad("\U0001f3af Practice"), callback_data="practice_this"),
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
        nav_row.append(InlineKeyboardButton(_pad("\u25c0\ufe0f Previous"), callback_data=f"vocab_page_{page - 1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(_pad("Next \u25b6\ufe0f"), callback_data=f"vocab_page_{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(_pad("\U0001f519 Back to Menu"), callback_data="back_to_menu")])
    return collapse_keyboard(keyboard, expanded=expanded)


def topic_suggestion(topic: str) -> InlineKeyboardMarkup:
    """Botoes apos sugestao de topico. SEM compressao — sempre visivel."""
    keyboard = [
        [
            InlineKeyboardButton(_pad("\u2705 Yes, let's talk!"), callback_data=f"start_topic_{topic}"),
            InlineKeyboardButton(_pad("\U0001f504 Another Topic"), callback_data="show_topics"),
        ],
        [InlineKeyboardButton(_pad("\U0001f519 Back to Menu"), callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def topics_menu(expanded: bool = False) -> InlineKeyboardMarkup:
    """Menu com a lista de topicos disponiveis (primeiros 5)."""
    keyboard = [
        [
            InlineKeyboardButton(_pad("\U0001f44b Greetings"), callback_data="start_topic_Greetings"),
            InlineKeyboardButton(_pad("\U0001f354 Food & Drinks"), callback_data="start_topic_Food & Drinks"),
        ],
        [
            InlineKeyboardButton(_pad("\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466 Family"), callback_data="start_topic_Family"),
            InlineKeyboardButton(_pad("\u26c5 Weather"), callback_data="start_topic_Weather"),
        ],
        [
            InlineKeyboardButton(_pad("\U0001f4c5 Daily Routine"), callback_data="start_topic_Daily Routine"),
            InlineKeyboardButton(_pad("\U0001f3b2 Random Topic"), callback_data="show_topics"),
        ],
        [InlineKeyboardButton(_pad("\U0001f519 Back to Menu"), callback_data="back_to_menu")],
    ]
    return collapse_keyboard(keyboard, expanded=expanded)


def level_selection_keyboard(current_level: str = "A1") -> InlineKeyboardMarkup:
    """Botoes para escolha de nivel de ingles. SEM compressao — sempre visivel."""
    row = []
    for level in ["A1", "A2", "B1"]:
        label = _pad(f"\u2705 {level}" if level == current_level else level)
        row.append(InlineKeyboardButton(label, callback_data=f"set_level_{level}"))
    return InlineKeyboardMarkup([row])


def voice_selection_keyboard(current_voice_id: str, current_speed: float = 1.0) -> InlineKeyboardMarkup:
    """Botoes para escolha de voz (Deepgram Aura) + velocidade."""
    VOICES = [
        ("aura-2-thalia-en", "Thalia"),
        ("aura-2-odysseus-en", "Odysseus"),
        ("aura-2-helena-en", "Helena"),
        ("aura-2-mars-en", "Mars"),
    ]

    keyboard = []
    for i in range(0, len(VOICES), 2):
        row = []
        for vid, name in VOICES[i:i+2]:
            label = _pad(f"\U0001f50a {name}" if vid == current_voice_id else name)
            row.append(InlineKeyboardButton(label, callback_data=f"set_voice_{vid}"))
        keyboard.append(row)

    speed_row = []
    for speed_val in SPEED_OPTIONS:
        emoji = ""
        if speed_val == 0.75:
            emoji = "\U0001f422 "
        elif speed_val == 1.25:
            emoji = "\U0001f407 "
        marker = " \u25cf" if speed_val == current_speed else ""
        label = f"{emoji}{speed_val}x{marker}"
        speed_row.append(InlineKeyboardButton(label, callback_data=f"set_speed_{speed_val}"))
    keyboard.append(speed_row)

    keyboard.append([InlineKeyboardButton(_pad("\U0001f519 Back to Menu"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def config_menu_keyboard() -> InlineKeyboardMarkup:
    """Botoes do menu de configuracao: Voice, Speed, Level."""
    keyboard = [
        [
            InlineKeyboardButton(_pad("\U0001f3a4 Voice"), callback_data="show_voice_picker"),
            InlineKeyboardButton(_pad("\u26a1 Speed"), callback_data="show_speed_picker"),
            InlineKeyboardButton(_pad("\U0001f4ca Level"), callback_data="show_level_picker"),
        ],
        [HIDE_BUTTON],
    ]
    return InlineKeyboardMarkup(keyboard)


def voice_picker_keyboard(current_voice_id: str) -> InlineKeyboardMarkup:
    """Botoes para escolha de voz (apenas vozes, sem velocidade)."""
    VOICES = [
        ("aura-2-thalia-en", "Thalia"),
        ("aura-2-odysseus-en", "Odysseus"),
        ("aura-2-helena-en", "Helena"),
        ("aura-2-mars-en", "Mars"),
    ]

    keyboard = []
    for i in range(0, len(VOICES), 2):
        row = []
        for vid, name in VOICES[i:i+2]:
            label = _pad(f"\U0001f50a {name}" if vid == current_voice_id else name)
            row.append(InlineKeyboardButton(label, callback_data=f"set_voice_{vid}"))
        keyboard.append(row)

    keyboard.append([HIDE_BUTTON])
    return InlineKeyboardMarkup(keyboard)


def speed_picker_keyboard(current_speed: float = 1.0) -> InlineKeyboardMarkup:
    """Botoes para escolha de velocidade (todos numa linha, distribuidos uniformemente)."""
    speed_row = []
    for speed_val in SPEED_OPTIONS:
        emoji = "\U0001f422 " if speed_val == 0.75 else ("\U0001f407 " if speed_val == 1.25 else "")
        marker = " \u25cf" if speed_val == current_speed else ""
        speed_row.append(InlineKeyboardButton(f"{emoji}{speed_val}x{marker}", callback_data=f"set_speed_{speed_val}"))
    keyboard = [speed_row, [HIDE_BUTTON]]
    return InlineKeyboardMarkup(keyboard)


def level_picker_keyboard(current_level: str = "A1") -> InlineKeyboardMarkup:
    """Botoes para escolha de nivel (dentro do config)."""
    row = []
    for level in ["A1", "A2", "B1"]:
        label = _pad(f"\u2705 {level}" if level == current_level else level)
        row.append(InlineKeyboardButton(label, callback_data=f"set_level_{level}"))
    return InlineKeyboardMarkup([row, [HIDE_BUTTON]])


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
    keyboard = [[InlineKeyboardButton(_pad("\U0001f519 Back to Menu"), callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)
