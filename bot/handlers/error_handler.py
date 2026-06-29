"""
LinguaBot --- Error Handler
Tratamento global de erros nao tratados.
"""

from __future__ import annotations

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unhandled errors in the bot."""
    logger.error("Excecao no handler: %s", context.error)

    # Log detalhado do erro
    tb = traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__
    )
    logger.error("Traceback: %s", "".join(tb))

    # Avisa o usuario se o erro veio de uma conversa
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "Sorry, something went wrong! Please try again in a moment. 🙏"
            )
        except Exception as e:
            logger.error("Erro ao enviar mensagem de erro: %s", e)
