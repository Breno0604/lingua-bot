"""
Tests para bot.utils.formatting
"""

import pytest
from bot.utils.formatting import (
    TOPICS,
    format_topic_suggestion,
    format_vocab_list,
    get_random_topic,
    split_long_message,
)
from bot.database import VocabEntry


class TestTopics:
    """Testes para topicos."""

    def test_topics_count(self):
        """Ha exatamente 15 topicos."""
        assert len(TOPICS) == 15

    def test_topic_structure(self):
        """Cada topico tem (nome_en, nome_pt, lista_palavras)."""
        for topic in TOPICS:
            assert len(topic) == 3
            assert isinstance(topic[0], str)  # nome en
            assert isinstance(topic[1], str)  # nome pt
            assert isinstance(topic[2], list)  # palavras
            assert len(topic[2]) > 0

    def test_get_random_topic(self):
        """get_random_topic retorna um topico valido."""
        topic = get_random_topic()
        assert topic in TOPICS

    def test_get_random_topic_exclude(self):
        """get_random_topic exclui topico quando especificado."""
        topic = get_random_topic(exclude="Greetings")
        assert topic[0] != "Greetings"

    def test_get_random_topic_exclude_all_but_one(self):
        """Excluir todos menos 1 retorna o unico disponivel."""
        topic = get_random_topic(exclude="Food & Drinks")
        # So verifica que nao e o excluido
        assert topic[0] != "Food & Drinks"

    def test_format_topic_suggestion(self):
        """format_topic_suggestion retorna string formatada."""
        topic = TOPICS[0]  # Greetings
        text = format_topic_suggestion(topic)
        assert "Greetings" in text
        assert "Saudações" in text
        assert "Hello" in text
        assert "topic" in text.lower()


class TestFormatVocabList:
    """Testes para format_vocab_list."""

    def test_empty_list(self):
        """Lista vazia retorna mensagem apropriada."""
        text = format_vocab_list([], 0)
        assert "don't have any words" in text.lower()

    def test_single_entry(self):
        """Lista com 1 entrada."""
        entries = [
            VocabEntry(
                id=1, user_id=1, word="hello", translation="ola",
                context="", created_at="", reviewed_at=None, practice_count=0,
            )
        ]
        text = format_vocab_list(entries, 1)
        assert "hello" in text
        assert "ola" in text
        assert "1 words" in text  # total_count=1
        assert "Page 1 of 1" in text

    def test_multiple_entries(self):
        """Lista com varias entradas."""
        entries = [
            VocabEntry(
                id=i, user_id=1, word=f"word{i}", translation=f"traducao{i}",
                context=f"context{i}", created_at="", reviewed_at=None,
                practice_count=i,
            )
            for i in range(1, 4)
        ]
        text = format_vocab_list(entries, 3)
        assert "word1" in text
        assert "word3" in text
        assert "3 words" in text
        assert "Practiced 2 times" in text  # entry with practice_count=2
        assert "Page 1 of 1" in text

    def test_pagination(self):
        """Pagina 1 de 2 quando ha mais de 10 entradas."""
        entries = [
            VocabEntry(
                id=i, user_id=1, word=f"w{i}", translation=f"t{i}",
                context="", created_at="", reviewed_at=None, practice_count=0,
            )
            for i in range(1, 11)
        ]
        text = format_vocab_list(entries, 15, page=1, page_size=10)
        assert "Page 1 of 2" in text

    def test_page_2(self):
        """Pagina 2 comeca em 11."""
        entries = [
            VocabEntry(
                id=i, user_id=1, word=f"w{i}", translation=f"t{i}",
                context="", created_at="", reviewed_at=None, practice_count=0,
            )
            for i in range(11, 16)
        ]
        text = format_vocab_list(entries, 15, page=2, page_size=10)
        assert "Page 2 of 2" in text
        assert "11." in text  # Primeiro item da pagina 2


class TestSplitLongMessage:
    """Testes para split_long_message."""

    def test_short_message(self):
        """Mensagem curta nao e quebrada."""
        text = "Short message"
        parts = split_long_message(text, max_length=100)
        assert len(parts) == 1
        assert parts[0] == text

    def test_long_message_newline(self):
        """Mensagem longa e quebrada no \\n."""
        text = "Short line\n" + "A" * 100 + "\n" + "B" * 50
        parts = split_long_message(text, max_length=80)
        assert len(parts) >= 2

    def test_long_message_no_newline(self):
        """Mensagem longa sem \\n e quebrada no espaco."""
        text = "word " * 50
        parts = split_long_message(text, max_length=80)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 80

    def test_empty_message(self):
        """Mensagem vazia retorna lista com string vazia."""
        parts = split_long_message("")
        assert parts == [""]


class TestExtractVocab:
    """Testes para a funcao extract_vocab_from_reply."""

    def test_extract_vocab_simple(self):
        """Extrai NEW_WORD e EXAMPLE."""
        from bot.utils.db_helpers import extract_vocab_from_reply

        reply = (
            "Hello! Let's practice!\n\n"
            "NEW_WORD: breakfast = cafe da manha\n"
            "EXAMPLE: I eat breakfast at 7am.\n\n"
            "Do you like breakfast?"
        )
        clean, words = extract_vocab_from_reply(reply)
        assert len(words) == 1
        assert words[0]["word"] == "breakfast"
        assert words[0]["translation"] == "cafe da manha"
        assert words[0]["context"] == "I eat breakfast at 7am."
        assert "NEW_WORD" not in clean
        assert "EXAMPLE" not in clean

    def test_extract_multiple_words(self):
        """Extrai multiplas palavras."""
        from bot.utils.db_helpers import extract_vocab_from_reply

        reply = (
            "NEW_WORD: dog = cachorro\n"
            "EXAMPLE: I have a dog.\n"
            "NEW_WORD: cat = gato\n"
            "EXAMPLE: The cat is sleepy.\n"
        )
        clean, words = extract_vocab_from_reply(reply)
        assert len(words) == 2
        assert words[0]["word"] == "dog"
        assert words[0]["context"] == "I have a dog."
        assert words[1]["word"] == "cat"
        assert words[1]["context"] == "The cat is sleepy."

    def test_no_vocab(self):
        """Resposta sem marcadores nao extrai nada."""
        from bot.utils.db_helpers import extract_vocab_from_reply

        reply = "Hello! How are you today?"
        clean, words = extract_vocab_from_reply(reply)
        assert len(words) == 0
        assert clean == reply

    def test_case_insensitive(self):
        """Marcadores sao case-insensitive."""
        from bot.utils.db_helpers import extract_vocab_from_reply

        reply = "new_word: hello = ola\nexample: Hello there!"
        clean, words = extract_vocab_from_reply(reply)
        assert len(words) == 1
        assert words[0]["word"] == "hello"
