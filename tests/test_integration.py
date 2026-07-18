"""
Tests de integração para ResponseValidator

Testa o fluxo completo de validação com dados reais.
"""

from __future__ import annotations

import pytest

from bot.services.response_validator import ResponseValidator


class TestResponseValidatorIntegration:
    """Testes de integração do ResponseValidator."""

    def setup_method(self):
        """Setup para cada teste."""
        self.validator = ResponseValidator()

    def test_validate_a1_real_response(self):
        """Valida resposta A1 real com palavras do top_800."""
        result = self.validator.validate(
            reply="I like cat. Do you like cat?",
            level="A1",
            user_message="What do you like?",
        )
        assert result.is_valid is True
        assert result.score >= 0.6

    def test_validate_a2_real_response(self):
        """Valida resposta A2 real sem idioms."""
        result = self.validator.validate(
            reply="I went to the store yesterday. Where did you go?",
            level="A2",
            user_message="I went to school",
        )
        assert result.is_valid is True
        assert result.score >= 0.6

    def test_validate_b1_real_response(self):
        """Valida resposta B1 real."""
        result = self.validator.validate(
            reply="I understand what you mean. What do you think about it?",
            level="B1",
            user_message="I think so",
        )
        assert result.is_valid is True
        assert result.score >= 0.6

    def test_validate_a1_with_non_common_words(self):
        """Resposta A1 com palavras nao-comuns e invalida."""
        result = self.validator.validate(
            reply="The numeral system is complex",
            level="A1",
            user_message="Tell me about numbers",
        )
        # "numeral" e "complex" nao estao no top_800
        assert result.is_valid is False
        assert "vocab_above_level" in result.issues

    def test_validate_a2_with_idiom(self):
        """Resposta A2 com idiom e invalida."""
        result = self.validator.validate(
            reply="That test was piece of cake",
            level="A2",
            user_message="How was the test?",
        )
        assert result.is_valid is False
        assert "idiom_found" in result.issues

    def test_validate_word_count_boundary(self):
        """Testa limite de palavras na fronteira."""
        # A1: 25 palavras (limite)
        words_25 = " ".join(["I"] * 25)
        result_25 = self.validator.validate(words_25, "A1", "test")
        assert result_25.is_valid is True

        # A1: 26 palavras (acima do limite)
        words_26 = " ".join(["I"] * 26)
        result_26 = self.validator.validate(words_26, "A1", "test")
        assert result_26.is_valid is False
        assert "too_long" in result_26.issues

    def test_score_weights(self):
        """Verifica que os pesos do score estao corretos."""
        # Resposta perfeita: score = 1.0
        result_perfect = self.validator.validate(
            reply="I like cat",
            level="A1",
            user_message="test",
        )
        assert result_perfect.score == 1.0

        # Resposta vazia: score = 0.0
        result_empty = self.validator.validate("", "A1", "test")
        assert result_empty.score == 0.0
