import logging
import re

from bot.database import BaseDatabase

logger = logging.getLogger(__name__)

NEW_WORD_PATTERN = re.compile(
    r"NEW_WORD:\s*(?P<word>[^=]+?)\s*=\s*(?P<translation>.+?)(?:\n|$)",
    re.IGNORECASE,
)
EXAMPLE_PATTERN = re.compile(
    r"EXAMPLE:\s*(?P<context>.+?)(?:\n|$)",
    re.IGNORECASE,
)


def extract_vocab_from_reply(reply: str) -> tuple[str, list[dict]]:
    """Extrai vocabulario (NEW_WORD / EXAMPLE) da resposta e retorna:
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


async def save_vocab_entries(
    db: BaseDatabase,
    user_id: int,
    words_found: list[dict],
    user_level: str,
) -> None:
    """Salva entradas de vocabulario no banco de dados."""
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


async def load_audio_prefs_from_db(context, user_id: int) -> None:
    """Carrega voice_id e tts_speed do banco para user_data se nao estiverem em cache."""
    if "voice_id" in context.user_data and "tts_speed" in context.user_data:
        return
    db: BaseDatabase = context.bot_data.get("db")
    if not db:
        return
    try:
        prefs = await db.get_user_preferences(user_id)
        if "voice_id" not in context.user_data and prefs.voice_id:
            context.user_data["voice_id"] = prefs.voice_id
        if "tts_speed" not in context.user_data and prefs.tts_speed is not None:
            context.user_data["tts_speed"] = prefs.tts_speed
    except Exception as e:
        logger.warning("Erro ao carregar preferencias de audio: %s", e)
