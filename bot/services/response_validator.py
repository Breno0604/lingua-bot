"""
LinguaBot --- Response Validator

Valida respostas geradas pelo LLM após geração.
Verifica comprimento, vocabulário e estrutura por nível.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultado da validação de uma resposta."""
    is_valid: bool
    issues: list[str] = field(default_factory=list)
    score: float = 0.0


class ResponseValidator:
    """Valida respostas do LLM baseado em regras por nível."""

    # Limites de comprimento por nível
    MAX_WORDS = {
        "A1": 25,
        "A2": 30,
        "B1": 35,
    }

    # Pesos para cálculo de score
    WEIGHT_LENGTH = 0.4
    WEIGHT_VOCABULARY = 0.4
    WEIGHT_STRUCTURE = 0.2

    def __init__(self):
        """Inicializa o validador e carrega listas de referência."""
        self._top_800_words: set[str] | None = None
        self._idioms_to_avoid: set[str] | None = None

    def _load_top_800_words(self) -> set[str]:
        """Carrega lista de 800 palavras mais comuns (lazy load)."""
        if self._top_800_words is None:
            words_file = Path(__file__).parent.parent.parent / "data" / "top_800_words.txt"
            if words_file.exists():
                self._top_800_words = {
                    line.strip().lower()
                    for line in words_file.read_text().splitlines()
                    if line.strip()
                }
                logger.debug("Loaded %d words from %s", len(self._top_800_words), words_file)
            else:
                logger.warning("Data file not found: %s — A1 vocabulary validation disabled", words_file)
                self._top_800_words = set()
        return self._top_800_words

    def _load_idioms_to_avoid(self) -> set[str]:
        """Carrega lista de idioms para evitar em A2 (lazy load)."""
        if self._idioms_to_avoid is None:
            idioms_file = Path(__file__).parent.parent.parent / "data" / "idioms_to_avoid.txt"
            if idioms_file.exists():
                self._idioms_to_avoid = {
                    line.strip().lower()
                    for line in idioms_file.read_text().splitlines()
                    if line.strip()
                }
                logger.debug("Loaded %d idioms from %s", len(self._idioms_to_avoid), idioms_file)
            else:
                logger.warning("Data file not found: %s — A2 idiom validation disabled", idioms_file)
                self._idioms_to_avoid = set()
        return self._idioms_to_avoid

    def validate(
        self,
        reply: str,
        level: str,
        user_message: str,  # TODO: kept for future context-aware validation (e.g. relevance check)
    ) -> ValidationResult:
        """
        Valida uma resposta gerada pelo LLM.

        Args:
            reply: Resposta gerada
            level: Nível do aluno (A1, A2, B1)
            user_message: Mensagem original do usuário

        Returns:
            ValidationResult com is_valid, issues e score
        """
        issues: list[str] = []

        if not reply or not reply.strip():
            return ValidationResult(
                is_valid=False,
                issues=["empty"],
                score=0.0,
            )

        words = reply.split()
        word_count = len(words)

        max_words = self.MAX_WORDS.get(level, 35)
        length_ok = word_count <= max_words
        if not length_ok:
            issues.append("too_long")

        vocab_ok = True
        if level == "A1":
            top_800 = self._load_top_800_words()
            if top_800:
                reply_words = {w.lower().strip(".,!?;:'\"") for w in words}
                non_common = reply_words - top_800
                significant_non_common = {
                    w for w in non_common
                    if len(w) > 2 and w not in ("new_word:", "example:")
                }
                if significant_non_common:
                    vocab_ok = False
                    issues.append("vocab_above_level")

        if level == "A2":
            idioms = self._load_idioms_to_avoid()
            if idioms:
                reply_lower = reply.lower()
                found_idioms = [idiom for idiom in idioms if idiom in reply_lower]
                if found_idioms:
                    vocab_ok = False
                    issues.append("idiom_found")

        structure_ok = word_count >= 3
        if not structure_ok:
            issues.append("too_short")

        score = (
            (self.WEIGHT_LENGTH if length_ok else 0.0) +
            (self.WEIGHT_VOCABULARY if vocab_ok else 0.0) +
            (self.WEIGHT_STRUCTURE if structure_ok else 0.0)
        )

        is_valid = len(issues) == 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
        )
