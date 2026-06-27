"""
LinguaBot --- Message Handler

Recebe mensagens de texto do usuario, chama o Groq,
aplica rate limiter, extrai vocabulario e envia a resposta com botoes.
"""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.elevenlabs import DEFAULT_VOICE_ID, ElevenLabsService
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.utils.keyboards import conversation_buttons
from bot.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Padrao para extrair vocabulario das respostas do Groq
# Formato: NEW_WORD: word = translation
NEW_WORD_PATTERN = re.compile(
    r"NEW_WORD:\s*(?P<word>[^=]+?)\s*=\s*(?P<translation>.+?)(?:\n|$)",
    re.IGNORECASE,
)
# Formato: EXAMPLE: sentence
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

    # Extrai todas as palavras no formato NEW_WORD
    for match in NEW_WORD_PATTERN.finditer(reply):
        word = match.group("word").strip()
        translation = match.group("translation").strip()
        words_found.append({"word": word, "translation": translation, "context": ""})

    # Extrai os exemplos
    examples = []
    for match in EXAMPLE_PATTERN.finditer(reply):
        examples.append(match.group("context").strip())

    # Associa exemplos as palavras (cada palavra recebe o exemplo seguinte)
    for i, word_info in enumerate(words_found):
        if i < len(examples):
            word_info["context"] = examples[i]

    # Remove as linhas de marcacao (NEW_WORD: ... e EXAMPLE: ...)
    clean = NEW_WORD_PATTERN.sub("", reply)
    clean = EXAMPLE_PATTERN.sub("", clean)
    # Remove linhas em branco extras (3+ \\n consecutivos -> 2)
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

    # Se for comando, ignora (outro handler cuida)
    if user_text.startswith("/"):
        return

    # Obtem servicos do bot_data
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

    # Rate limiter: verifica soft limit
    if rate_limiter:
        rate_info = rate_limiter.check_and_increment(user_id)
        if rate_info["warning"]:
            # Avisa mas nao bloqueia (soft limit)
            await update.message.reply_text(rate_info["warning"])

    # Mostra indicador de digitacao
    await update.message.chat.send_action(action="typing")

    # Gerencia contexto da conversa
    conv = conversation_mgr.get_or_create(user_id)
    conv.add_user_message(user_text)

    # Gera historico formatado
    history = conv.get_formatted_history()

    # Obtem nivel do usuario para adaptar o system prompt
    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"

    # Chama Groq com nivel do usuario
    try:
        reply = await groq.generate_reply(history, user_text, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar resposta: %s", e)
        reply = None

    if reply:
        conv.add_assistant_message(reply)

        # Extrai vocabulario e limpa a resposta
        clean_reply, words_found = _extract_and_clean_reply(reply)

        # Salva vocabulario no banco de dados
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
                # Erro de BD nao deve interromper a conversa
                logger.error(
                    "Erro ao salvar vocabulario para user %d: %s", user_id, e
                )

        # Se a resposta ficou vazia apos limpar os marcadores,
        # usa o texto original
        display_text = clean_reply if clean_reply else reply

        # Marca tela como conversa e mostra botoes COMPRIMIDOS
        context.user_data["screen_type"] = "conversation"

        # Gera audio da resposta (apenas para conversas)
        elevenlabs: ElevenLabsService = context.bot_data.get("elevenlabs")
        audio_bytes = None
        usage_warning = ""
        if elevenlabs:
            voice_id = context.user_data.get("voice_id", DEFAULT_VOICE_ID)
            audio_bytes = await elevenlabs.generate_speech(display_text, voice_id=voice_id)
            if audio_bytes:
                usage_warning = elevenlabs.get_usage_warning()

        final_text = display_text + usage_warning if usage_warning else display_text

        if audio_bytes:
            # Marca que esta mensagem tem audio para o botao Listen Again
            context.user_data["has_audio"] = True

            # Envia como nota de voz + texto
            await update.message.reply_voice(
                voice=audio_bytes,
                caption=final_text,
                reply_markup=conversation_buttons(expanded=False, has_audio=True),
            )
        else:
            # Se o usuario escolheu uma voz diferente da padrao e o audio falhou,
            # avisa brevemente (mas nao atrapalha a conversa)
            voice_id = context.user_data.get("voice_id", DEFAULT_VOICE_ID)
            audio_note = ""
            if voice_id != DEFAULT_VOICE_ID:
                audio_note = (
                    "\n\n\U0001f3b6 *Audio tip:* The voice you selected isn't generating audio. "
                    "Use /voice to try a different one."
                )

            await update.message.reply_text(
                final_text + audio_note,
                reply_markup=conversation_buttons(expanded=False),
            )
    else:
        await update.message.reply_text(
            "Sorry, I'm having trouble thinking right now. "
            "Let's try again in a moment! \u23f3"
        )
