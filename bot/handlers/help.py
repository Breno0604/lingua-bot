"""
LinguaBot --- Help Handler
Lista de comandos disponiveis e dicas de uso.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command. Shows available commands and tips."""
    help_text = (
        "\U0001f4d6 **LinguaBot Commands**\n\n"
        "**Basics:**\n"
        "\u2022 `/start` - Welcome & main menu\n"
        "\u2022 `/help` - Show this help message\n\n"
        "**Conversation:**\n"
        "\u2022 Just type anything to start a conversation!\n"
        "\u2022 I'll respond in **English** and gently correct your mistakes\n"
        "\u2022 Try saying something about your day! \U0001f5e3\ufe0f\n\n"
        "**Commands:**\n"
        "\u2022 `/level` - Check or change your English level (A1, A2, B1)\n"
        "\u2022 `/voice` - Choose a voice for audio responses (5 voices available)\n"
        "\u2022 `/reset` - Clear conversation history and start fresh\n"
        "\u2022 `/vocab` - View your saved vocabulary list (filtered by level)\n"
        "\u2022 `/topic` - Get a suggested topic to practice\n\n"
        "**Levels:** \U0001f4ca\n"
        "\u2022 **A1** - Iniciante: simple words, short sentences\n"
        "\u2022 **A2** - B\u00e1sico: everyday vocabulary, longer sentences\n"
        "\u2022 **B1** - Intermedi\u00e1rio: varied vocabulary, natural expressions\n"
        "\u2022 Use `/level` anytime to switch!\n\n"
        "**Buttons:** \U0001f447\n"
        "\u2022 Responses show just \u2795 **More Options** to keep chat clean\n"
        "\u2022 Tap it to reveal: \U0001f4dd More Examples, \U0001f4d6 Explain, \U0001f3af Practice\n"
        "\u2022 Tap \u25c0 **Hide Options** to hide them again\n\n"
        "**Tips for learning:** \U0001f4a1\n"
        "\u2022 Don't worry about mistakes - that's how we learn!\n"
        "\u2022 Try to answer in full sentences\n"
        "\u2022 Use the buttons below my responses for extra practice\n"
        "\u2022 Practice a little every day for best results\n\n"
        "Ready to start? Just type something! \U0001f680"
    )

    keyboard = [
        [InlineKeyboardButton("\U0001f4ac Start Talking!", callback_data="start_conversation")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
