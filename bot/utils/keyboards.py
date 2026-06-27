"""
LinguaBot --- Keyboards

Menus e botoes inline usados nos handlers.
Centraliza a definicao dos teclados para facilitar manutencao.

Todos os teclados agora suportam compressao via collapse_keyboard:
- expanded=False (padrao): mostra apenas "➕ More Options"
- expanded=True: mostra todos os botoes + "◀ Hide Options"
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Botoes de controle de compressao
MORE_BUTTON = InlineKeyboardButton("\u2795 More Options", callback_data="show_more_options")
HIDE_BUTTON = InlineKeyboardButton("\u25c0 Hide Options", callback_data="hide_options")


def collapse_keyboard(
    expanded_keyboard: list[list[InlineKeyboardButton]],
    expanded: bool = False,
) -> InlineKeyboardMarkup:
    """Encapsula um teclado inline com comportamento de expandir/recolher.

    Args:
        expanded_keyboard: O teclado completo (lista de linhas de botoes).
        expanded: Se True, mostra todos os botoes + Hide Options.
                  Se False (padrao), mostra apenas "+ More Options".

    Returns:
        InlineKeyboardMarkup com o estado apropriado.
    """
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
    keyboard = [
        [
            InlineKeyboardButton("\U0001f4dd More Examples", callback_data="more_examples"),
            InlineKeyboardButton("\U0001f4d6 Explain This Word", callback_data="explain_word"),
        ],
        [
            InlineKeyboardButton("\U0001f3af Practice This", callback_data="practice_this"),
        ],
    ]
    return collapse_keyboard(keyboard, expanded=expanded)


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


def back_to_menu_button() -> InlineKeyboardMarkup:
    """Botao simples de voltar ao menu. SEM compressao — ja e um unico botao."""
    keyboard = [[InlineKeyboardButton("\U0001f519 Back to Menu", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)
