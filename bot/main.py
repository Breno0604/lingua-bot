"""
LinguaBot --- Main Entry Point

Modos de operacao:
  - polling (dev local): python bot/main.py
  - webhook (Render/producao): uvicorn bot.webhook_server:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import load_config
from bot.database import create_database
from bot.handlers.audio import handle_audio
from bot.handlers.callbacks import handle_callback
from bot.handlers.commands import reset_command, topic_command, vocab_command
from bot.handlers.error_handler import error_handler
from bot.handlers.help import help_command
from bot.handlers.level_command import level_command
from bot.handlers.message import handle_message
from bot.handlers.voice_command import voice_command
from bot.handlers.start import start
from bot.services.conversation import ConversationManager
from bot.services.deepgram import DeepgramService
from bot.services.deepgram_tts import DeepgramTTSService
from bot.services.elevenlabs import ElevenLabsService
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.services.tts_orchestrator import TTSOrchestrator
from bot.utils.rate_limiter import RateLimiter

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Cria e configura a aplicacao do bot com todos os handlers."""
    config = load_config()
    db = create_database(config)
    groq = GroqService(config)
    conversation_mgr = ConversationManager(max_turns=config.max_history_turns)
    rate_limiter = RateLimiter(daily_limit=config.daily_limit, persist=True)
    level_mgr = LevelManager(default_level="A1", db=db)

    application = Application.builder().token(config.bot_token).build()

    # Armazena dependencias no bot_data para acesso nos handlers
    application.bot_data["config"] = config
    application.bot_data["db"] = db
    application.bot_data["groq"] = groq
    application.bot_data["conversation_mgr"] = conversation_mgr
    application.bot_data["rate_limiter"] = rate_limiter
    application.bot_data["level_manager"] = level_mgr

    # ── Servicos de Audio ──
    # Hierarchy: Deepgram Aura (primario) -> ElevenLabs (fallback)
    #
    # Fluxo dos handlers:
    #   1. message.py / audio.py / callbacks.py
    #      -> tenta deepgram_tts.generate_speech(text, voice_id)
    #   2. Se falhou -> tenta elevenlabs.generate_speech(text) [Rachel]
    #   3. Se ambos falharam -> resposta sem audio

    # ── STT (Speech-to-Text) ──
    if config.deepgram_api_key:
        deepgram_stt_service = DeepgramService(config.deepgram_api_key)
        application.bot_data["deepgram"] = deepgram_stt_service
        application.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, handle_audio)
        )
        logger.info("Deepgram STT inicializado")

    # ── TTS (Text-to-Speech) ──
    deepgram_tts_service = None
    elevenlabs_service = None

    if config.deepgram_api_key:
        deepgram_tts_service = DeepgramTTSService(api_key=config.deepgram_api_key)
        application.bot_data["deepgram_tts"] = deepgram_tts_service
        logger.info("Deepgram Aura TTS inicializado (primario)")

    if config.elevenlabs_api_key:
        elevenlabs_service = ElevenLabsService(api_key=config.elevenlabs_api_key)
        application.bot_data["elevenlabs"] = elevenlabs_service
        logger.info("ElevenLabs TTS inicializado" +
                    (" (fallback)" if deepgram_tts_service else ""))

    if deepgram_tts_service or elevenlabs_service:
        tts_orchestrator = TTSOrchestrator(
            deepgram_tts=deepgram_tts_service,
            elevenlabs=elevenlabs_service,
        )
        application.bot_data["tts_orchestrator"] = tts_orchestrator
        logger.info("TTSOrchestrator inicializado")

    if not config.deepgram_api_key and not config.elevenlabs_api_key:
        logger.info("Nenhuma chave de API de audio configurada — pulando servicos de audio")

    # --- Handlers de Comandos ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("vocab", vocab_command))
    application.add_handler(CommandHandler("topic", topic_command))
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("voice", voice_command))

    # --- Handler de Callbacks (botoes inline) ---
    application.add_handler(CallbackQueryHandler(handle_callback))

    # --- Handler de Mensagens de Texto ---
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # --- Handler para Erros ---
    application.add_error_handler(error_handler)

    return application


def run_polling() -> None:
    """Inicia o bot em modo polling (desenvolvimento local)."""
    logger.info("Iniciando LinguaBot em modo POLLING...")
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    config = load_config()

    if config.bot_mode == "webhook":
        logger.info(
            "Modo webhook detectado. Inicie com: uvicorn bot.webhook_server:app"
        )
        sys.exit(0)
    else:
        run_polling()
