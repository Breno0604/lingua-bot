"""
LinguaBot --- Audio Handler

Recebe mensagens de voz/audio do Telegram:
  1. Faz download do arquivo de audio
  2. Envia para Deepgram STT
  3. Texto transcrito entra no fluxo normal da conversa
  4. Resposta e gerada com texto + audio (Deepgram Aura primario + ElevenLabs fallback)

So processa audio se o usuario ja tiver conversa ativa.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.deepgram import DeepgramService
from bot.services.deepgram_tts import DEFAULT_VOICE_ID as DG_DEFAULT_VOICE_ID
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.utils.keyboards import conversation_buttons
from bot.handlers.message import _extract_and_clean_reply

logger = logging.getLogger(__name__)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de voz/audio do usuario.

    Fluxo:
      1. Verifica se ha conversa ativa
      2. Download do audio
      3. STT com Deepgram
      4. Mostra previa do que foi entendido
      5. Chama Groq
      6. Gera audio com Deepgram Aura (+ ElevenLabs fallback)
      7. Envia texto + audio
    """
    if not update.message or not (update.message.voice or update.message.audio):
        return

    user_id = update.effective_user.id

    # Obtem servicos
    groq: GroqService = context.bot_data.get("groq")
    conversation_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    db: BaseDatabase = context.bot_data.get("db")
    level_mgr: LevelManager = context.bot_data.get("level_manager")
    deepgram_stt: DeepgramService = context.bot_data.get("deepgram")
    deepgram_tts = context.bot_data.get("deepgram_tts")
    elevenlabs = context.bot_data.get("elevenlabs")

    if not groq or not conversation_mgr or not db or not deepgram_stt:
        logger.error("Servicos de audio nao inicializados no bot_data")
        await update.message.reply_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f"
        )
        return

    # 1. So processa se ja houver conversa ativa
    conv = conversation_mgr.get_or_create(user_id)
    if not conv.get_history():
        await update.message.reply_text(
            "Let's start with text first! Say something like 'Hello!' to begin. \U0001f60a"
        )
        return

    # 2. Mostra indicador "processando..."
    await update.message.chat.send_action(action="record_audio")

    # 3. Download do audio
    try:
        voice = update.message.voice or update.message.audio
        file = await voice.get_file()
        audio_bytes = await file.download_as_bytearray()
    except Exception as e:
        logger.error("Erro ao baixar audio: %s", e)
        await update.message.reply_text(
            "Sorry, I couldn't download your audio. Please try again! \U0001f3a4"
        )
        return

    # 4. STT com Deepgram
    transcribed_text = await deepgram_stt.transcribe_audio(bytes(audio_bytes))

    if not transcribed_text:
        await update.message.reply_text(
            "Sorry, I couldn't understand the audio. "
            "Please try again or type your message! \U0001f3a4"
        )
        return

    # 5. Sempre mostra previa do que foi entendido
    preview = await update.message.reply_text(
        f"\U0001f3a4 *You said:* {transcribed_text}\n\n"
        "Let me respond...",
        parse_mode="Markdown",
    )

    # 6. Entra no fluxo normal da conversa (Groq)
    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"
    conv.add_user_message(transcribed_text)
    history = conv.get_formatted_history()

    try:
        reply = await groq.generate_reply(history, transcribed_text, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar resposta do audio via Groq: %s", e)
        reply = None

    if not reply:
        await update.message.reply_text(
            "Sorry, I'm having trouble thinking right now. "
            "Let's try again in a moment! \u23f3"
        )
        return

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
        except Exception as e:
            logger.error(
                "Erro ao salvar vocabulario para user %d: %s", user_id, e
            )

    display_text = clean_reply if clean_reply else reply

    # 7. Envia texto imediatamente (antes do audio)
    await update.message.reply_text(
        display_text,
        reply_markup=conversation_buttons(expanded=False),
    )

    # 8. Gera audio da resposta
    # Primario: Deepgram Aura | Fallback: ElevenLabs Rachel
    audio_bytes = None

    if deepgram_tts:
        voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
        audio_bytes = await deepgram_tts.generate_speech(display_text, voice_id=voice_id)

    # Fallback: ElevenLabs
    if not audio_bytes and elevenlabs:
        logger.info("Deepgram Aura falhou, usando ElevenLabs fallback (audio msg)")
        audio_bytes = await elevenlabs.generate_speech(display_text)

    if audio_bytes:
        await update.message.reply_voice(voice=audio_bytes)
    else:
        voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
        if voice_id != DG_DEFAULT_VOICE_ID:
            await update.message.reply_text(
                "\U0001f3b6 *Audio tip:* The voice you selected isn't generating audio. "
                "Use /voice to try a different one.",
                parse_mode="Markdown",
            )
