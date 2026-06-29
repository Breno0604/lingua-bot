"""
LinguaBot --- Message Handler

Recebe mensagens de texto do usuario, chama o Groq,
aplica rate limiter, extrai vocabulario e envia a resposta com botoes.
Gera audio com Deepgram Aura (primario) + ElevenLabs (fallback).
"""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.deepgram_tts import DEFAULT_VOICE_ID as DG_DEFAULT_VOICE_ID
from bot.services.groq import GroqService
from bot.handlers.voice_command import _load_audio_prefs_from_db
from bot.services.level_manager import LevelManager
from bot.services.tts_orchestrator import TTSOrchestrator
from bot.utils.keyboards import DEFAULT_SPEED_BY_LEVEL, cleanup_old_buttons, conversation_buttons
from bot.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Padrao para extrair vocabulario das respostas do Groq
NEW_WORD_PATTERN = re.compile(
    r"NEW_WORD:\s*(?P<word>[^=]+?)\s*=\s*(?P<translation>.+?)(?:\n|$)",
    re.IGNORECASE,
)
EXAMPLE_PATTERN = re.compile(
    r"EXAMPLE:\s*(?P<context>.+?)(?:\n|$)",
    re.IGNORECASE,
)


def _extract_and_clean_reply(reply: str) -> tuple[str, list[dict]]:
    """
    Extrai vocabulario (NEW_WORD / EXAMPLE) da resposta e retorna:
    - O texto limpo (sem os marcadores)
    - Uma lista de dicionarios com word, translation, context
    """
    words_found = []

    for match in NEW_WORD_PATTERN.finditer(reply):
        word = match.group("word").strip()
        translation = match.group("translation").strip()
        words_found.append({"word": word, "translation": translation, "context": ""})

    examples = []
    for match in EXAMPLE_PATTERN.finditer(reply):
        examples.append(match.group("context").strip())

    for i, word_info in enumerate(words_found):
        if i < len(examples):
            word_info["context"] = examples[i]

    clean = NEW_WORD_PATTERN.sub("", reply)
    clean = EXAMPLE_PATTERN.sub("", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = clean.strip()

    return clean, words_found


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

        clean_reply, words_found = _extract_and_clean_reply(reply)

        for word_info in words_found:
            try:
                await db.save_vocab(
                    user_id=user_id,
                    word=word_info["word"],
                    translation=word_info["translation"],
                    context=word_info["context"],
                    level=user_level,
                )
                logger.info(
                    "Vocabulario salvo: %s = %s (user %d)",
                    word_info["word"],
                    word_info["translation"],
                    user_id,
                )
            except Exception as e:
                logger.error(
                    "Erro ao salvar vocabulario para user %d: %s", user_id, e
                )

        display_text = clean_reply if clean_reply else reply

        context.user_data["screen_type"] = "conversation"

        # Remove botoes de mensagens anteriores
        await cleanup_old_buttons(context, update.effective_chat.id)

        # Carrega preferencias do banco (voz, velocidade) se necessario
        await _load_audio_prefs_from_db(context, user_id)

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
