"""
LinguaBot --- Formatting Utils

Utilitarios para formatacao de mensagens:
  - Formatacao da lista de vocabulario para exibicao
  - Quebra de mensagens longas (acima de 4000 chars)
  - Formatacao de data/hora
"""

from __future__ import annotations

from bot.database import VocabEntry


def format_vocab_list(
    entries: list[VocabEntry],
    total_count: int,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """
    Formata a lista de vocabulario para exibicao.

    Formato:
    📚 Your Vocabulary (12 words)

    1. breakfast = café da manhã
       "I eat breakfast at 7am."
       ⭐ Practiced 3 times

    2. weather = clima / tempo
       "The weather is sunny today."
       ⭐ Practiced 1 time

    Page 1 of 2
    """
    if not entries:
        return (
            "📚 **Your Vocabulary**\n\n"
            "You don't have any words saved yet.\n"
            "Start a conversation and I'll introduce new words! 🚀"
        )

    lines = [f"📚 **Your Vocabulary ({total_count} words)**\n"]

    start_idx = (page - 1) * page_size + 1
    for i, entry in enumerate(entries, start=start_idx):
        lines.append(f"{i}. **{entry.word}** = {entry.translation}")
        if entry.context:
            lines.append(f'   *"{entry.context}"*')
        if entry.practice_count > 0:
            times = "time" if entry.practice_count == 1 else "times"
            lines.append(f"   ⭐ Practiced {entry.practice_count} {times}")
        lines.append("")

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    lines.append(f"Page {page} of {total_pages}")

    return "\n".join(lines)


def split_long_message(text: str, max_length: int = 4000) -> list[str]:
    """
    Quebra uma mensagem longa em partes menores.

    Args:
        text: Texto completo.
        max_length: Tamanho maximo por parte (default 4000 para Telegram).

    Returns:
        Lista de strings, cada uma com no maximo max_length caracteres.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        # Tenta quebrar no ultimo \\n antes do limite
        cut = text.rfind("\n", 0, max_length)
        if cut == -1 or cut < max_length // 2:
            # Sem \\n bom, quebra no ultimo espaco
            cut = text.rfind(" ", 0, max_length)
            if cut == -1 or cut < max_length // 2:
                cut = max_length

        parts.append(text[:cut].strip())
        text = text[cut:].strip()

    return parts


def get_welcome_text(first_name: str) -> str:
    """Retorna o texto de boas-vindas para primeiro acesso."""
    return (
        f"\U0001f44b Hello {first_name}! I'm **LinguaBot**, your English teacher! \U0001f389\n\n"
        "I'm here to help you practice English. We can talk about many topics, "
        "and I'll gently correct your mistakes along the way.\n\n"
        "**First, let's set your English level** so I can adapt to you!"
    )


def get_level_choice_text(first_name: str) -> str:
    """Texto para escolha de nivel (usuario ja tem nivel)."""
    return (
        f"\U0001f44b Hello {first_name}! I'm **LinguaBot**, your English teacher! \U0001f389\n\n"
        "I'm here to help you practice English.\n\n"
        "**Great! Let's start practicing!** \U0001f680\n\n"
        "You can change your level anytime with /level"
    )


TOPICS = [
    ("Greetings", "Saudações", ["Hello", "Good morning", "How are you?", "Nice to meet"]),
    ("Food & Drinks", "Comida e Bebida", ["Breakfast", "lunch", "dinner", "water", "rice", "bread"]),
    ("Family", "Família", ["Mother", "father", "brother", "sister", "baby"]),
    ("Weather", "Clima", ["Sunny", "rainy", "cold", "hot", "windy", "cloudy"]),
    ("Daily Routine", "Rotina Diária", ["Wake up", "eat", "work", "sleep", "shower", "brush"]),
    ("Animals", "Animais", ["Dog", "cat", "bird", "fish", "horse", "cow"]),
    ("Numbers & Colors", "Números e Cores", ["One-ten", "red", "blue", "green", "yellow", "black", "white"]),
    ("Shopping", "Compras", ["Buy", "sell", "price", "cheap", "expensive", "money"]),
    ("Transport", "Transporte", ["Car", "bus", "train", "bike", "airport", "station"]),
    ("Body & Health", "Corpo e Saúde", ["Head", "hand", "foot", "doctor", "sick", "hospital"]),
    ("House & Furniture", "Casa e Móveis", ["Room", "kitchen", "bed", "table", "chair", "door", "window"]),
    ("Work & School", "Trabalho e Escola", ["Teacher", "student", "office", "homework", "class"]),
    ("Clothes & Seasons", "Roupas e Estações", ["Shirt", "pants", "shoes", "summer", "winter", "spring"]),
    ("Hobbies & Games", "Hobbies e Jogos", ["Read", "play", "run", "sing", "dance", "game", "music"]),
    ("Places in the City", "Lugares na Cidade", ["Park", "market", "library", "bank", "restaurant", "museum"]),
]


def get_random_topic(exclude: str | None = None) -> tuple:
    """Retorna um topico aleatorio da lista fixa, opcionalmente excluindo um."""
    import random

    available = [t for t in TOPICS if t[0] != exclude]
    return random.choice(available) if available else random.choice(TOPICS)


def format_topic_suggestion(topic: tuple) -> str:
    """Formata uma sugestao de topico para exibicao."""
    name_en, name_pt, vocab = topic
    vocab_examples = ", ".join(vocab[:4])

    return (
        f"🎯 **Let's practice a topic!**\n\n"
        f"How about **{name_en}** ({name_pt})?\n\n"
        f"Some words you can use: *{vocab_examples}...*\n\n"
        f"Would you like to talk about this topic? 😊"
    )
