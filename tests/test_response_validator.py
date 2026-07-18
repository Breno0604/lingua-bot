"""
Tests para bot.services.response_validator

Testa a validação de respostas por nível.
"""

from __future__ import annotations

import pytest
from bot.services.response_validator import ResponseValidator, ValidationResult


class TestResponseValidator:
    """Testes para ResponseValidator."""

    def test_validator_initialization(self):
        """ResponseValidator inicializa corretamente."""
        validator = ResponseValidator()
        assert validator is not None

    def test_validate_a1_within_limits(self):
        """Resposta A1 dentro dos limites é válida."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="Hello! I like cat. Do you like dog?",
            level="A1",
            user_message="I like pizza"
        )
        assert result.is_valid is True
        assert result.score >= 0.6

    def test_validate_a1_too_long(self):
        """Resposta A1 com mais de 25 palavras é inválida."""
        validator = ResponseValidator()
        # 30 palavras - acima do limite de 25
        long_reply = " ".join(["word"] * 30)
        result = validator.validate(
            reply=long_reply,
            level="A1",
            user_message="Hello"
        )
        assert result.is_valid is False
        assert "too_long" in result.issues

    def test_validate_a2_within_limits(self):
        """Resposta A2 dentro dos limites é válida."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="That's interesting! I went to the store yesterday. Where did you go?",
            level="A2",
            user_message="I went to school"
        )
        assert result.is_valid is True

    def test_validate_a2_too_long(self):
        """Resposta A2 com mais de 30 palavras é inválida."""
        validator = ResponseValidator()
        long_reply = " ".join(["word"] * 35)
        result = validator.validate(
            reply=long_reply,
            level="A2",
            user_message="Hello"
        )
        assert result.is_valid is False
        assert "too_long" in result.issues

    def test_validate_b1_within_limits(self):
        """Resposta B1 dentro dos limites é válida."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="I understand what you mean. Many people feel that way. What do you think about it?",
            level="B1",
            user_message="I think so"
        )
        assert result.is_valid is True

    def test_validate_b1_too_long(self):
        """Resposta B1 com mais de 35 palavras é inválida."""
        validator = ResponseValidator()
        long_reply = " ".join(["word"] * 40)
        result = validator.validate(
            reply=long_reply,
            level="B1",
            user_message="Hello"
        )
        assert result.is_valid is False
        assert "too_long" in result.issues

    def test_validate_common_word_check(self):
        """Verificação de palavras comuns para A1."""
        validator = ResponseValidator()
        # Resposta com palavras comuns
        result = validator.validate(
            reply="I am happy today",
            level="A1",
            user_message="How are you?"
        )
        assert result.is_valid is True

    def test_score_calculation(self):
        """Cálculo de score está correto."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="Great!",
            level="A1",
            user_message="Hello"
        )
        assert 0.0 <= result.score <= 1.0

    def test_empty_reply_invalid(self):
        """Resposta vazia é inválida."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="",
            level="A1",
            user_message="Hello"
        )
        assert result.is_valid is False
        assert "empty" in result.issues

    def test_whitespace_only_invalid(self):
        """Resposta só com espaços é inválida."""
        validator = ResponseValidator()
        result = validator.validate(
            reply="   ",
            level="A1",
            user_message="Hello"
        )
        assert result.is_valid is False
        assert "empty" in result.issues

    def test_level_specific_rules(self):
        """Regras específicas por nível são aplicadas."""
        validator = ResponseValidator()
        # A1 com frase ok
        result_a1 = validator.validate(
            reply="I like cat",
            level="A1",
            user_message="What do you like?"
        )
        # B1 com frase ok
        result_b1 = validator.validate(
            reply="I like my cat and dog",
            level="B1",
            user_message="I think so"
        )
        assert result_a1.is_valid is True
        assert result_b1.is_valid is True

    def test_validation_result_dataclass(self):
        """ValidationResult contém campos corretos."""
        result = ValidationResult(
            is_valid=True,
            issues=[],
            score=0.8
        )
        assert result.is_valid is True
        assert result.issues == []
        assert result.score == 0.8
