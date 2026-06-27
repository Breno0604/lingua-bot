"""
LinguaBot --- Callback Handlers

Processa cliques em botoes inline:
  - Navegacao: menu, voltar
  - Acao: more_examples, explain_word, practice_this
  - Vocabulario: paginacao
  - Topicoss: iniciar conversa sobre topico especifico
  - Expandir/recolher: show_more_options, hide_options
"""

import asyncio
import logging

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


# ──────────────────────────────────────────────
# Helpers de compressao de botoes
# ──────────────────────────────────────────────

def _set_screen_type(context: ContextTypes.DEFAULT_TYPE, screen_type: str, **kwargs) -> None:
    """Armazena o tipo de tela atual e dados auxiliares no user_data."""
    context.user_data["screen_type"] = screen_type
    for key, value in kwargs.items():
        context.user_data[key] = value


def _get_keyboard_for_screen(context: ContextTypes.DEFAULT_TYPE, expanded: bool = False):
    """Retorna o teclado apropriado para a tela atual, comprimido ou expandido."""
    screen_type = context.user_data.get("screen_type", "conversation")
    page = context.user_data.get("page", 1)
    total_pages = context.user_data.get("total_pages", 1)

    if screen_type == "menu":
        return main_menu(expanded=expanded)
    elif screen_type == "vocab":
        return vocab_pagination(page, total_pages, expanded=expanded)
    elif screen_type == "topics":
        return topics_menu(expanded=expanded)
    else:  # "conversation"
        return conversation_buttons(expanded=expanded)


async def _expand_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expande os botoes: substitui '+ More Options' pelos botoes reais + Hide."""
    original_text = query.message.text or ""

    # Feedback visual rapido: mostra loading antes de expandir
    try:
        await query.edit_message_text(
            original_text + "\n\n✨ Loading...",
            parse_mode="Markdown",
        )
        await asyncio.sleep(0.3)
    except Exception as exc:
        logger.warning("Loading animation skipped: %s", exc)

    expanded_keyboard = _get_keyboard_for_screen(context, expanded=True)
    try:
        await query.edit_message_text(
            original_text,
            reply_markup=expanded_keyboard,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Falha ao expandir botoes: %s", exc)


async def _collapse_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recolhe os botoes: substitui botoes por '+ More Options'."""
    collapsed_keyboard = _get_keyboard_for_screen(context, expanded=False)
    await query.edit_message_reply_markup(reply_markup=collapsed_keyboard)


# ──────────────────────────────────────────────
# Roteador Principal
# ──────────────────────────────────────────────

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

    # Expansao/recolhimento de botoes
    elif data == "show_more_options":
        await _expand_options(query, context)
    elif data == "hide_options":
        await _collapse_options(query, context)

    # Botoes de conversa
    elif data == "more_examples":
        await _more_examples(query, context)
    elif data == "explain_word":
        await _explain_word(query, context)
    elif data == "practice_this":
        await _practice_this(query, context)

    # Paginacao de vocabulario (navegacao entre paginas: mantem expandido)
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
            "I didn't understand that option. Try /help to see what I can do! \U0001f60a",
            reply_markup=back_to_menu_button(),
        )


# ──────────────────────────────────────────────
# Handlers Especificos
# ──────────────────────────────────────────────

async def _set_level(query, context: ContextTypes.DEFAULT_TYPE, level: str) -> None:
    """Define o nivel do usuario e confirma. SEM compressao — nivel e sempre visivel."""
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
    """Exibe o menu principal (comprimido)."""
    from bot.handlers.start import _get_welcome_text

    user = query.from_user
    first_name = user.first_name if user else "there"
    welcome = _get_welcome_text(first_name)

    _set_screen_type(context, "menu")

    await query.edit_message_text(
        welcome,
        reply_markup=main_menu(expanded=False),
        parse_mode="Markdown",
    )


async def _show_how_it_works(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe explicacao de como o bot funciona."""
    text = (
        "\u2753 **How LinguaBot Works**\n\n"
        "I'm your personal English teacher! Here's how to get the most out of me:\n\n"
        "**1. Just start talking** \U0001f4ac\n"
        "Type anything in English (or Portuguese) and I'll respond in English.\n\n"
        "**2. I adapt to your level** \U0001f4ca\n"
        "Choose your English level with `/level` and I'll adjust:\n"
        "\u2022 **A1** - Simple words, short sentences, basic grammar\n"
        "\u2022 **A2** - Everyday vocabulary, longer sentences\n"
        "\u2022 **B1** - Varied vocabulary, natural expressions\n"
        "You can change anytime!\n\n"
        "**3. I correct gently** \U0001f4dd\n"
        "When you make mistakes, I'll:\n"
        "\u2022 Point out what you did right first \u2705\n"
        "\u2022 Offer a simple correction \U0001f4d6\n"
        "\u2022 Keep corrections short so you can keep talking\n\n"
        "**4. Clean buttons** \U0001f447\n"
        "After each reply, just one button appears: \u2795 **More Options**\n"
        "Tap it to access:\n"
        "\u2022 \U0001f4dd More Examples - see more sentences\n"
        "\u2022 \U0001f4d6 Explain This Word - simple explanation\n"
        "\u2022 \U0001f3af Practice This - mini exercise\n"
        "Tap \u25c0 **Hide Options** to hide them again.\n\n"
        "**5. New vocabulary** \U0001f4da\n"
        "I introduce new words naturally during conversation.\n"
        "Use /vocab to see all your saved words!\n\n"
        "**6. Practice topics** \U0001f3af\n"
        "Use /topic to get a fun topic to talk about:\n"
        "\u2022 Food, Family, Weather, Animals, and 11 more!\n\n"
        "**Tips for best results** \U0001f4a1\n"
        "\u2022 Don't worry about mistakes - that's how we learn!\n"
        "\u2022 Try to write in full sentences\n"
        "\u2022 Practice a little every day\n"
        "\u2022 Use /reset to start a fresh conversation\n\n"
        "Ready? Just type something! \U0001f680"
    )

    await query.edit_message_text(
        text,
        reply_markup=back_to_menu_button(),
        parse_mode="Markdown",
    )


async def _start_conversation(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia uma conversa com sugestao de topico. SEM compressao — botoes sempre visiveis."""
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    await query.edit_message_text(
        f"Great! Let's start practicing! \U0001f389\n\n{suggestion}",
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )


async def _show_vocab(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o vocabulario do usuario (pagina 1, comprimido)."""
    await _show_vocab_page(query, context, page=1)


async def _show_vocab_page(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    """Exibe uma pagina especifica do vocabulario, filtrada por nivel.

    Quando o usuario esta navegando entre paginas (vocab_page_n),
    o estado permanece EXPANDIDO para facilitar a navegacao.
    Quando vem de outra tela, comeca COMPRIMIDO.
    """
    user_id = query.from_user.id
    db: BaseDatabase = context.bot_data.get("db")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not db:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f",
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
            "Sorry, I couldn't get your vocabulary right now. \U0001f64f",
            reply_markup=back_to_menu_button(),
        )
        return

    from bot.utils.formatting import format_vocab_list

    text = format_vocab_list(entries, total, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Se veio de callback vocab_page_n (navegacao), mantem EXPANDIDO
    # Se veio de show_vocab (entrando na tela), comeca COMPRIMIDO
    came_from_nav = query.data and query.data.startswith("vocab_page_")

    _set_screen_type(context, "vocab", page=page, total_pages=total_pages)

    if entries:
        reply_markup = vocab_pagination(page, total_pages, expanded=came_from_nav)
    else:
        reply_markup = back_to_menu_button()

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def _show_topics(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu de topicos (comprimido)."""
    topic = get_random_topic()
    suggestion = format_topic_suggestion(topic)

    _set_screen_type(context, "topics")

    await query.edit_message_text(
        suggestion,
        reply_markup=topic_suggestion(topic[0]),
        parse_mode="Markdown",
    )


async def _start_topic(query, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
    """
    Inicia uma conversa sobre um topico especifico.
    Resposta vem EXPANDIDA para que o usuario ja veja as opcoes.
    """
    user_id = query.from_user.id
    groq: GroqService = context.bot_data.get("groq")
    conv_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not groq or not conv_mgr:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f",
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

    # Cria a mensagem de prompt
    user_prompt = f"I want to practice speaking about {name_en}. Can you help me?"
    conv.add_user_message(user_prompt)
    history = conv.get_formatted_history()

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

    _set_screen_type(context, "conversation")

    if reply:
        conv.add_assistant_message(reply)
        text = (
            f"\U0001f3af **Let's talk about {name_en}!**\n\n"
            f"{reply}"
        )
    else:
        text = (
            f"\U0001f3af **Let's talk about {name_en}!**\n\n"
            f"Great choice! {name_en} is a fun topic to practice.\n\n"
            f"Some words you can use: {vocab_list}\n\n"
            f"Tell me something about your favorite {name_en.lower()}! \U0001f60a"
        )
        conv.add_assistant_message(text)

    await query.edit_message_text(
        text,
        reply_markup=conversation_buttons(expanded=True),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# Acoes da Conversa (More Examples, Explain, Practice)
# ──────────────────────────────────────────────

async def _more_examples(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera mais exemplos sobre o ultimo topico da conversa. Resposta EXPANDIDA."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants MORE EXAMPLES of the word or grammar structure "
            "from our last exchange. Provide 2-3 more simple example sentences "
            "using the same vocabulary or structure. Keep it A1-A2 level."
        ),
        loading_text="\U0001f4dd Generating more examples...",
        expanded=True,
    )


async def _explain_word(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explica uma palavra da conversa. Resposta EXPANDIDA."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants you to EXPLAIN A WORD from our conversation. "
            "Choose the most recent or important word you introduced. "
            "Explain it simply in English (A1-A2 level). Give a definition, "
            "the Portuguese translation, and an example sentence. "
            "Format: WORD: [word] = [translation] - [simple explanation]"
        ),
        loading_text="\U0001f4d6 Looking up word explanation...",
        expanded=True,
    )


async def _practice_this(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera um pequeno exercicio de pratica. Resposta EXPANDIDA."""
    await _call_groq_for(
        query, context,
        prompt_suffix=(
            "The student wants to PRACTICE the topic or vocabulary from "
            "our conversation. Create a very simple exercise (A1-A2 level). "
            "It could be: fill in the blank, make a sentence with a word, "
            "or answer a simple question. Only 1 exercise. "
            "Format: EXERCISE: [the exercise]"
        ),
        loading_text="\U0001f3af Creating a practice exercise...",
        expanded=True,
    )


async def _call_groq_for(
    query, context: ContextTypes.DEFAULT_TYPE,
    prompt_suffix: str,
    loading_text: str,
    expanded: bool = False,
) -> None:
    """
    Helper para chamar o Groq com um prompt baseado na conversa atual.

    Args:
        query: O callback query do Telegram.
        context: O context do bot.
        prompt_suffix: Texto adicional a ser adicionado ao prompt.
        loading_text: Mensagem mostrada enquanto carrega.
        expanded: Se True, resposta vem com botoes expandidos.
    """
    user_id = query.from_user.id
    groq: GroqService = context.bot_data.get("groq")
    conv_mgr: ConversationManager = context.bot_data.get("conversation_mgr")
    level_mgr: LevelManager = context.bot_data.get("level_manager")

    if not groq or not conv_mgr:
        await query.edit_message_text(
            "Sorry, I'm not ready yet. Please try /start again! \U0001f64f"
        )
        return

    # Mostra mensagem de carregamento
    await query.edit_message_text(loading_text)

    user_level = level_mgr.get_level(user_id) if level_mgr else "A1"

    conv = conv_mgr.get_or_create(user_id)
    history = conv.get_formatted_history()

    if not history:
        await query.edit_message_text(
            "Let's start a conversation first! Type something and I'll help you practice! \U0001f60a",
            reply_markup=back_to_menu_button(),
        )
        return

    try:
        reply = await groq.generate_reply(history, prompt_suffix, level=user_level)
    except Exception as e:
        logger.error("Erro ao gerar resposta do callback: %s", e)
        reply = None

    _set_screen_type(context, "conversation")

    if reply:
        conv.add_assistant_message(reply)
        conv.add_user_message(prompt_suffix)

        await query.edit_message_text(
            reply,
            reply_markup=conversation_buttons(expanded=expanded),
        )
    else:
        await query.edit_message_text(
            "Sorry, I had trouble thinking of something. Let's try again! \U0001f60a",
            reply_markup=conversation_buttons(expanded=False),
        )
