"""
LinguaBot --- Keyboards

Menus e botoes inline usados nos handlers.
Centraliza a definicao dos teclados para facilitar manutencao.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """Menu principal exibido no /start."""
    keyboard = [
        [
            InlineKeyboardButton("💬 Start a Conversation", callback_data="start_conversation"),
            InlineKeyboardButton("❓ How it Works", callback_data="how_it_works"),
        ],
        [
            InlineKeyboardButton("📚 My Vocabulary", callback_data="show_vocab"),
            InlineKeyboardButton("🎯 Practice Topics", callback_data="show_topics"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def conversation_buttons() -> InlineKeyboardMarkup:
    """Botoes exibidos apos cada resposta do bot."""
    keyboard = [
        [
            InlineKeyboardButton("📝 More Examples", callback_data="more_examples"),
            InlineKeyboardButton("📖 Explain This Word", callback_data="explain_word"),
        ],
        [
            InlineKeyboardButton("🎯 Practice This", callback_data="practice_this"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def vocab_pagination(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Botoes de paginacao para a lista de vocabulario."""
    keyboard = []

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"vocab_page_{page - 1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"vocab_page_{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def topic_suggestion(topic: str) -> InlineKeyboardMarkup:
    """Botoes apos sugestao de topico."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, let's talk!", callback_data=f"start_topic_{topic}"),
            InlineKeyboardButton("🔄 Another Topic", callback_data="show_topics"),
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def topics_menu() -> InlineKeyboardMarkup:
    """Menu com a lista de topicos disponiveis (primeiros 5)."""
    keyboard = [
        [
            InlineKeyboardButton("👋 Greetings", callback_data="start_topic_Greetings"),
            InlineKeyboardButton("🍔 Food & Drinks", callback_data="start_topic_Food & Drinks"),
        ],
        [
            InlineKeyboardButton("👨‍👩‍👧‍👦 Family", callback_data="start_topic_Family"),
            InlineKeyboardButton("🌤️ Weather", callback_data="start_topic_Weather"),
        ],
        [
            InlineKeyboardButton("📅 Daily Routine", callback_data="start_topic_Daily Routine"),
        ],
        [
            InlineKeyboardButton("🎲 Random Topic", callback_data="show_topics"),
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def level_selection_keyboard(current_level: str = "A1") -> InlineKeyboardMarkup:
    """Botoes para escolha de nivel de ingles."""
    from bot.services.level_manager import LevelManager

    keyboard = []
    for level in LevelManager.VALID_LEVELS:
        label = LevelManager.LEVEL_LABELS[level]
        if level == current_level:
            label = f"\u2705 {label}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_level_{level}")])
    return InlineKeyboardMarkup(keyboard)


def back_to_menu_button() -> InlineKeyboardMarkup:
    """Botao simples de voltar ao menu."""
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)
