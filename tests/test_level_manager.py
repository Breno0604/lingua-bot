"""Tests for LevelManager service."""

import pytest
from bot.services.level_manager import LevelManager


class TestLevelManagerInitialization:
    """Testes de inicializacao do LevelManager."""

    def test_default_level_is_a1(self):
        mgr = LevelManager()
        assert mgr.default_level == "A1"

    def test_custom_default_level(self):
        mgr = LevelManager(default_level="B1")
        assert mgr.default_level == "B1"

    def test_valid_levels(self):
        assert LevelManager.VALID_LEVELS == ["A1", "A2", "B1"]

    def test_level_labels_exist(self):
        for level in LevelManager.VALID_LEVELS:
            assert level in LevelManager.LEVEL_LABELS

    def test_level_confirmations_exist(self):
        for level in LevelManager.VALID_LEVELS:
            assert level in LevelManager.LEVEL_CONFIRMATIONS


class TestLevelManagerGetLevel:
    """Testes de leitura do nivel."""

    def test_unset_user_returns_default(self):
        mgr = LevelManager()
        assert mgr.get_level(123) == "A1"

    def test_custom_default_for_unset_user(self):
        mgr = LevelManager(default_level="B1")
        assert mgr.get_level(456) == "B1"

    def test_returns_set_level(self):
        mgr = LevelManager()
        mgr.set_level(789, "B1")
        assert mgr.get_level(789) == "B1"

    def test_multiple_users_independent(self):
        mgr = LevelManager()
        mgr.set_level(1, "A2")
        mgr.set_level(2, "B1")
        assert mgr.get_level(1) == "A2"
        assert mgr.get_level(2) == "B1"
        assert mgr.get_level(3) == "A1"  # default


class TestLevelManagerSetLevel:
    """Testes de definicao do nivel."""

    def test_set_valid_level(self):
        mgr = LevelManager()
        assert mgr.set_level(1, "A2") is True
        assert mgr.get_level(1) == "A2"

    def test_set_all_valid_levels(self):
        mgr = LevelManager()
        for level in ["A1", "A2", "B1"]:
            assert mgr.set_level(1, level) is True
            assert mgr.get_level(1) == level

    def test_set_invalid_level_returns_false(self):
        mgr = LevelManager()
        assert mgr.set_level(1, "C1") is False
        assert mgr.get_level(1) == "A1"  # nao mudou

    def test_set_lowercase_level(self):
        mgr = LevelManager()
        assert mgr.set_level(1, "a1") is False  # case sensitive
        assert mgr.get_level(1) == "A1"

    def test_set_empty_level(self):
        mgr = LevelManager()
        assert mgr.set_level(1, "") is False
        assert mgr.get_level(1) == "A1"


class TestLevelManagerHelpers:
    """Testes dos metodos auxiliares."""

    def test_get_label_a1(self):
        assert LevelManager().get_label("A1") == "A1 - Iniciante"

    def test_get_label_a2(self):
        assert LevelManager().get_label("A2") == "A2 - B\u00e1sico"

    def test_get_label_b1(self):
        assert LevelManager().get_label("B1") == "B1 - Intermedi\u00e1rio"

    def test_get_label_unknown(self):
        assert LevelManager().get_label("C1") == "C1"

    def test_get_confirmation_a1(self):
        text = LevelManager().get_confirmation("A1")
        assert "simple words" in text
        assert len(text) > 10

    def test_get_confirmation_unknown(self):
        assert LevelManager().get_confirmation("C1") == ""

    def test_has_level_false_initially(self):
        mgr = LevelManager()
        assert mgr.has_level(999) is False

    def test_has_level_true_after_set(self):
        mgr = LevelManager()
        mgr.set_level(999, "A2")
        assert mgr.has_level(999) is True

    def test_remove_clears_level(self):
        mgr = LevelManager()
        mgr.set_level(1, "B1")
        mgr.remove(1)
        assert mgr.has_level(1) is False
        assert mgr.get_level(1) == "A1"  # volta ao default

    def test_remove_nonexistent_user(self):
        mgr = LevelManager()
        mgr.remove(999)  # nao deve exception
        assert mgr.has_level(999) is False
