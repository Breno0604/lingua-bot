"""
LinguaBot --- Callback Handlers

Processa cliques em botoes inline:
  - Navegacao: menu, voltar
  - Acao: more_examples, explain_word, practice_this
  - Vocabulario: paginacao
  - Topicoss: iniciar conversa sobre topico especifico
"""

import logging
import random

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import BaseDatabase
from bot.services.conversation import ConversationManager
from bot.services.groq import GroqService
from bot.services.level_manager import LevelManager
from bot.utils.formatting import TOPICS, format_topic_suggestion, get_random_topic
from bot.utils.keyboards import (
    back_to_menu_button,
    conversation_buttons,
    level_selection_keyboard,
    main_menu,
    topic_suggestion,
    topics_menu,
    vocab_pagination,
)

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roteia callbacks para os handlers apropriados."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Navegacao basica
    if data == "back_to_menu":
        await _show_menu(query, context)
    elif data == "how_it_works":
        await _show_how_it_works(query, context)
    elif data == "start_conversation":
        await _start_conversation(query, context)
    elif data == "show_vocab":
        await _show_vocab(query, context)
    elif data == "show_topics":
        await _show_topics(query, context)

    # Botoes de conversa
    elif data == "more_examples":
        await _more_examples(query, context)
    elif data == "explain_word":
        await _explain_word(query, context)
    elif data == "practice_this":
        await _practice_this(query, context)

    # Paginacao de vocabulario
    elif data.startswith("vocab_page_"):
        page = int(data.split("_")[-1])
        await _show_vocab_page(query, context, page)

    # Iniciar topico especifico
    elif data.startswith("start_topic_"):
        topic_name = data[len("start_topic_"):]
        await _start_topic(query, context, topic_name)

    # Gerenciamento de nivel
    elif data.startswith("set_level_"):
        level = data[len("set_level_"):]
        await _set_level(query, context, level)

    else:
        logger.warning("Callback nao reconhecido: %s", data)
        await query.edit_message_text(
            "I didn't understand that option. Try /help to see what I can do! 😊",
            reply_markup=back_to_menu_button(),
        )


async def _set_level(query, context: ContextTypes.DEFAULT_TYPE, level: str) -> None:
    """Define o nivel do usuario e confirma."""
    user_id = query.from_user.id
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not level_mgr:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f"
        )
        return

    if not level_mgr.set_level(user_id, level):
        await query.edit_message_text(
            f"Invalid level: {level}. Please choose A1, A2, or B1.",
            reply_markup=back_to_menu_button(),
        )
        return

    label = level_mgr.get_label(level)
    confirmation = level_mgr.get_confirmation(level)

    text = (
        f"\u2705 **Level updated to {label}!**\n\n"
        f"{confirmation}\n\n"
        "You can change your level anytime with /level"
    )

    await query.edit_message_text(
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def _show_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu principal."""
    from bot.handlers.start import _get_welcome_text

    user = query.from_user
    first_name = user.first_name if user else "there"
    welcome = _get_welcome_text(first_name)

    await query.edit_message_text(
        welcome,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def _show_how_it_works(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe explicacao de como o bot funciona."""
    text = (
        "❓ **How LinguaBot Works**\n\n"
        "I'm your personal English teacher! Here's how to get the most out of me:\n\n"
        "**1. Just start talking** 💬\n"
        "Type anything in English (or Portuguese) and I'll respond in English.\n\n"
        "**2. I correct gently** 📝\n"
        "When you make mistakes, I'll:\n"
        "• Point out what you did right first ✅\n"
        "• Offer a simple correction 📖\n"
        "• No more than 1-2 corrections at a time\n\n"
        "**3. New vocabulary** 📚\n"
        "I introduce new words naturally. Use /vocab to see them all!\n\n"
        "**4. Practice tools** 🎯\n"
        "Use the buttons below my messages for extra practice.\n"
        "Use /topic to get a conversation topic.\n\n"
        "**5. Tips for best results** 💡\n"
        "• Don't worry about mistakes!\n"
        "• Try to write in full sentences\n"
        "• Practice a little every day\n"
        "• Use /reset to start a fresh conversation\n\n"
        "Ready? Just type something! 🚀"
    )

    await query.edit_message_text(
        text,
        reply_markup=back_to_menu_button(),
        parse_mode="Markdown",
    )


async def _start_conversation(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia uma conversa com sugestao de topico."""
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    await query.edit_message_text(
        f"Great! Let's start practicing! 🎉\n\n{suggestion}",
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )


async def _show_vocab(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o vocabulario do usuario (pagina 1)."""
    await _show_vocab_page(query, context, page=1)


async def _show_vocab_page(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    """Exibe uma pagina especifica do vocabulario, filtrada por nivel."""
    user_id = query.from_user.id
    db: BaseDatabase = context.bot_data.get("db")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not db:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! 🙏",
            reply_markup=back_to_menu_button(),
        )
        return

    # Filtra pelo nivel atual do usuario
    user_level = level_mgr.get_level(user_id) if level_mgr else None
    page_size = 10

    try:
        total = await db.get_vocab_count(user_id, level=user_level)
        entries = await db.get_vocab(user_id, page=page, page_size=page_size, level=user_level)
    except Exception as e:
        logger.error("Erro ao buscar vocabulario: %s", e)
        await query.edit_message_text(
            "Sorry, I couldn't get your vocabulary right now. 🙏",
            reply_markup=back_to_menu_button(),
        )
        return

    from bot.utils.formatting import format_vocab_list

    text = format_vocab_list(entries, total, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    reply_markup = vocab_pagination(page, total_pages) if entries else back_to_menu_button()

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def _show_topics(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu de topicos ou sugestao aleatoria."""
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    await query.edit_message_text(
        suggestion,
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )


async def _start_topic(query, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
    """
    Inicia uma conversa sobre um topico especifico.
    Encontra o topico na lista e gera uma mensagem inicial via Groq.
    """
    user_id = query.from_user.id
    groq: GroqService = context.bot_data.get("groq")
    conv_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not groq or not conv_mgr:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! 🙏",
            reply_markup=back_to_menu_button(),
        )
        return

    # Encontra o topico na lista
    topic_info = None
    for t in TOPICS:
        if t[0] == topic_name:
            topic_info = t
            break

    if not topic_info:
        topic_info = get_random_topic()

    name_en, name_pt, vocab = topic_info
    vocab_list = ", ".join(vocab)

    # Reseta a conversa e inicia com o topico
    conv_mgr.reset(user_id)
    conv = conv_mgr.get_or_create(user_id)

    # Cria a mensagem de prompt: o aluno pediu para conversar sobre o topico
    user_prompt = f"I want to practice speaking about {name_en}. Can you help me?"
    conv.add_user_message(user_prompt)
    history = conv.get_formatted_history()

    # Instrucao adicional para o modelo gerar uma introducao adequada
    instruction = (
        f"[INSTRUCTION] The student wants to practice the topic '{name_en}' ({name_pt}). "
        f"Introduce the topic with 2-3 simple sentences in English (A1-A2 level). "
        f"Suggest words the student can use: {vocab_list}. "
        f"End with a question to engage the student."
    )

    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"

    try:
        reply = await groq.generate_reply(history, instruction, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar introducao do topico: %s", e)
        reply = None

    if reply:
        conv.add_assistant_message(reply)

        text = (
            f"🎯 **Let's talk about {name_en}!**\n\n"
            f"{reply}"
        )
    else:
        # Fallback: mensagem pre-definida
        text = (
            f"🎯 **Let's talk about {name_en}!**\n\n"
            f"Great choice! {name_en} is a fun topic to practice.\n\n"
            f"Some words you can use: {vocab_list}\n\n"
            f"Tell me something about your favorite {name_en.lower()}! 😊"
        )
        conv.add_assistant_message(text)

    await query.edit_message_text(
        text,
        reply_markup=conversation_buttons(),
        parse_mode="Markdown",
    )


async def _more_examples(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera mais exemplos sobre o ultimo topico da conversa."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants MORE EXAMPLES of the word or grammar structure "
            "from our last exchange. Provide 2-3 more simple example sentences "
            "using the same vocabulary or structure. Keep it A1-A2 level."
        ),
        loading_text="📝 Generating more examples...",
    )


async def _explain_word(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explica uma palavra da conversa."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants you to EXPLAIN A WORD from our conversation. "
            "Choose the most recent or important word you introduced. "
            "Explain it simply in English (A1-A2 level). Give a definition, "
            "the Portuguese translation, and an example sentence. "
            "Format: WORD: [word] = [translation] - [simple explanation]"
        ),
        loading_text="📖 Looking up word explanation...",
    )


async def _practice_this(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera um pequeno exercicio de pratica."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants to PRACTICE the topic or vocabulary from "
            "our conversation. Create a very simple exercise (A1-A2 level). "
            "It could be: fill in the blank, make a sentence with a word, "
            "or answer a simple question. Only 1 exercise. "
            "Format: EXERCISE: [the exercise]"
        ),
        loading_text="🎯 Creating a practice exercise...",
    )


async def _call_groq_for(
    query, context: ContextTypes.DEFAULT_TYPE,
    prompt_suffix: str,
    loading_text: str,
) -> None:
    """
    Helper para chamar o Groq com um prompt baseado na conversa atual.

    Args:
        query: O callback query do Telegram.
        context: O context do bot.
        prompt_suffix: Texto adicional a ser adicionado ao prompt.
        loading_text: Mensagem mostrada enquanto carrega.
    """
    user_id = query.from_user.id
    groq: GroqService = context.bot_data.get("groq")
    conv_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not groq or not conv_mgr:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! 🙏"
        )
        return

    # Mostra mensagem de carregamento
    await query.edit_message_text(loading_text)

    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"

    conv = conv_mgr.get_or_create(user_id)
    history = conv.get_formatted_history()

    if not history:
        await query.edit_message_text(
            "Let's start a conversation first! Type something and I'll help you practice! 😊",
            reply_markup=back_to_menu_button(),
        )
        return

    try:
        reply = await groq.generate_reply(history, prompt_suffix, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar resposta do callback: %s", e)
        reply = None

    if reply:
        conv.add_assistant_message(reply)
        conv.add_user_message(prompt_suffix)

        await query.edit_message_text(
            reply,
            reply_markup=conversation_buttons(),
        )
    else:
        await query.edit_message_text(
            "Sorry, I had trouble thinking of something. Let's try again! 😊",
            reply_markup=conversation_buttons(),
        )
