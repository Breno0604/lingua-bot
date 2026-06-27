"""
LinguaBot --- Help Handler
Lista de comandos disponiveis e dicas de uso.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command. Shows available commands and tips."""
    help_text = (
        "📖 **LinguaBot Commands**\n\n"
        "**Basics:**\n"
        "• `/start` - Welcome & main menu\n"
        "• `/help` - Show this help message\n\n"
        "**Conversation:**\n"
        "• Just type anything to start a conversation!\n"
        "• I'll respond in English and correct your mistakes\n"
        "• Try saying something about your day! 🗣️\n\n"
        "**Commands:**\n"
        "• `/reset` - Clear conversation history and start fresh\n"
        "• `/vocab` - View your saved vocabulary list\n"
        "• `/topic` - Get a suggested topic to practice\n\n"
        "**Tips for learning:** 💡\n"
        "• Don't worry about mistakes - that's how we learn!\n"
        "• Try to answer in full sentences\n"
        "• Use the buttons below my responses for extra practice\n"
        "• Practice a little every day for best results\n\n"
        "Ready to start? Just type something! 🚀"
    )

    keyboard = [
        [InlineKeyboardButton("💬 Start Talking!", callback_data="start_conversation")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
