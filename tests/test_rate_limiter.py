"""
Tests para bot.utils.rate_limiter
"""

from unittest.mock import patch

import pytest
from bot.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """Testes para RateLimiter."""

    def test_initial_state(self):
        """RateLimiter comeca sem uso."""
        rl = RateLimiter(daily_limit=100, persist=False)
        status = rl.get_status(12345)
        assert status["current"] == 0
        assert status["remaining"] == 100
        assert status["limit"] == 100

    def test_first_increment(self):
        """Primeiro incremento conta corretamente."""
        rl = RateLimiter(daily_limit=100, persist=False)
        result = rl.check_and_increment(12345)
        assert result["current"] == 1
        assert result["remaining"] == 99
        assert result["allowed"] is True
        assert result["warning"] is None

    def test_multiple_increments(self):
        """Multiplos incrementos contam corretamente."""
        rl = RateLimiter(daily_limit=100, persist=False)
        for i in range(5):
            result = rl.check_and_increment(12345)

        assert result["current"] == 5
        assert result["remaining"] == 95

    def test_warning_at_80_percent(self):
        """Aviso aparece ao atingir 80% do limite."""
        rl = RateLimiter(daily_limit=10, persist=False)
        for i in range(7):
            result = rl.check_and_increment(12345)

        # 7 < 8 (80%), ainda sem warning
        assert result["warning"] is None

        # 8 = 80%, deve ter warning
        result = rl.check_and_increment(12345)
        assert result["warning"] is not None
        assert "almost reached" in result["warning"]
        assert result["remaining"] == 2

    def test_warning_at_limit(self):
        """Aviso de limite atingido aparece ao atingir 100%."""
        rl = RateLimiter(daily_limit=3, persist=False)
        for i in range(3):
            result = rl.check_and_increment(12345)

        assert result["current"] == 3
        assert result["remaining"] == 0
        assert result["warning"] is not None
        assert "reached your daily" in result["warning"]

    def test_continuacao_apos_limite(self):
        """Usuario pode continuar mesmo apos o limite (soft limit)."""
        rl = RateLimiter(daily_limit=3, persist=False)
        for i in range(5):
            result = rl.check_and_increment(12345)

        assert result["allowed"] is True  # Soft limit: nunca bloqueia
        assert result["current"] == 5

    def test_get_status_sem_incrementar(self):
        """get_status nao incrementa o contador."""
        rl = RateLimiter(daily_limit=100, persist=False)
        rl.check_and_increment(12345)

        status = rl.get_status(12345)
        assert status["current"] == 1  # Nao incrementou

    def test_reset_user(self):
        """reset_user zera o contador do usuario."""
        rl = RateLimiter(daily_limit=100, persist=False)
        rl.check_and_increment(12345)
        rl.check_and_increment(12345)

        rl.reset_user(12345)
        status = rl.get_status(12345)
        assert status["current"] == 0

    def test_multiple_users_independentes(self):
        """Usuarios diferentes tem contadores independentes."""
        rl = RateLimiter(daily_limit=100, persist=False)
        rl.check_and_increment(1)
        rl.check_and_increment(1)
        rl.check_and_increment(2)

        assert rl.get_status(1)["current"] == 2
        assert rl.get_status(2)["current"] == 1
        assert rl.get_status(3)["current"] == 0

    def test_different_daily_limits(self):
        """Cada instancia pode ter limite diferente."""
        rl1 = RateLimiter(daily_limit=10, persist=False)
        rl2 = RateLimiter(daily_limit=50, persist=False)

        assert rl1.daily_limit == 10
        assert rl2.daily_limit == 50
