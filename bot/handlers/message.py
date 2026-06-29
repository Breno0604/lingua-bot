"""
LinguaBot --- Message Handler

Recebe mensagens de texto do usuario, chama o Groq,
aplica rate limiter, extrai vocabulario e envia a resposta com botoes.
Gera audio com Deepgram Aura (primario) + ElevenLabs (fallback).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.deepgram_tts import DEFAULT_VOICE_ID as DG_DEFAULT_VOICE_ID
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.services.tts_orchestrator import TTSOrchestrator
from bot.utils.db_helpers import extract_vocab_from_reply, load_audio_prefs_from_db, save_vocab_entries
from bot.constants import DEFAULT_SPEED_BY_LEVEL
from bot.utils.keyboards import cleanup_old_buttons, conversation_buttons
from bot.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages from users.
    Routes to Groq for response generation.
    """
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    if user_text.startswith("/"):
        return

    groq: GroqService = context.bot_data.get("groq")
    conversation_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    db: BaseDatabase = context.bot_data.get("db")
    rate_limiter: RateLimiter = context.bot_data.get("rate_limiter")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not groq or not conversation_mgr or not db:
        logger.error("Servicos nao inicializados no bot_data")
        await update.message.reply_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f"
        )
        return

    if rate_limiter:
        rate_info = rate_limiter.check_and_increment(user_id)
        if rate_info["warning"]:
            await update.message.reply_text(rate_info["warning"])

    await update.message.chat.send_action(action="typing")

    conv = conversation_mgr.get_or_create(user_id)
    conv.add_user_message(user_text)

    history = conv.get_formatted_history()

    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"

    try:
        reply = await groq.generate_reply(history, user_text, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar resposta: %s", e)
        reply = None

    if reply:
        conv.add_assistant_message(reply)

        clean_reply, words_found = extract_vocab_from_reply(reply)

        await save_vocab_entries(db, user_id, words_found, user_level)

        display_text = clean_reply if clean_reply else reply

        context.user_data["screen_type"] = "conversation"

        # Remove botoes de mensagens anteriores
        await cleanup_old_buttons(context, update.effective_chat.id)

        # Carrega preferencias do banco (voz, velocidade) se necessario
        await load_audio_prefs_from_db(context, user_id)

        # ── Gera audio via TTSOrchestrator (Deepgram Aura + ElevenLabs fallback) ──
        tts: TTSOrchestrator = context.bot_data.get("tts_orchestrator")
        audio_bytes = None
        if tts:
            voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
            speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
            audio_bytes = await tts.generate_audio(display_text, voice_id=voice_id, speed=speed)

        if audio_bytes:
            # Audio pronto: texto sem botoes + voz com botoes acoplados
            text_msg = await update.message.reply_text(display_text)
            voice_msg = await update.message.reply_voice(
                voice=audio_bytes,
                reply_markup=conversation_buttons(expanded=False),
            )
            # Rastreia apenas a mensagem de voz (tem os botoes)
            context.user_data.setdefault("button_msg_ids", []).append(voice_msg.message_id)
        else:
            # Sem audio: envia texto com botoes diretamente
            voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
            if voice_id != DG_DEFAULT_VOICE_ID:
                display_text += (
                    "\n\n\U0001f3b6 *Audio tip:* The voice you selected isn't generating audio. "
                    "Use /voice to try a different one."
                )
            msg = await update.message.reply_text(
                display_text,
                reply_markup=conversation_buttons(expanded=False),
            )
            context.user_data.setdefault("button_msg_ids", []).append(msg.message_id)
    else:
        await update.message.reply_text(
            "Sorry, I'm having trouble thinking right now. "
            "Let's try again in a moment! \u23f3"
        )
