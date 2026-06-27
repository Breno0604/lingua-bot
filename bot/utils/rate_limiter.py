"""
LinguaBot --- Rate Limiter

Soft limit de mensagens por usuario (100/dia por padrao).
Nao bloqueia, apenas avisa o usuario quando esta proximo do limite.

Implementacao:
  - Dicionario em memoria {user_id: (data, contagem)}
  - Reset a meia-noite UTC
  - Persistencia opcional em arquivo JSON
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PERSISTENCE_FILE = os.path.join(DATA_DIR, "rate_limits.json")


class RateLimiter:
    """Controla o limite suave de mensagens por usuario."""

    def __init__(self, daily_limit: int = 100, persist: bool = True):
        self.daily_limit = daily_limit
        self.persist = persist
        # {user_id: (date_str, count)}
        self._usage: Dict[int, Tuple[str, int]] = {}
        self._load()

    def _get_today(self) -> str:
        """Retorna a data atual no formato YYYY-MM-DD (UTC)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self) -> None:
        """Carrega dados de uso do arquivo JSON."""
        if not self.persist:
            return
        try:
            if os.path.exists(PERSISTENCE_FILE):
                with open(PERSISTENCE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id_str, (date_str, count) in data.items():
                        self._usage[int(user_id_str)] = (date_str, count)
        except Exception as e:
            logger.warning("Erro ao carregar rate limits: %s", e)

    def _save(self) -> None:
        """Salva dados de uso no arquivo JSON."""
        if not self.persist:
            return
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(PERSISTENCE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._usage, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Erro ao salvar rate limits: %s", e)

    def check_and_increment(self, user_id: int) -> dict:
        """
        Verifica o limite e incrementa o contador.

        Returns:
            dict com:
              - allowed: sempre True (soft limit)
              - current: contagem atual
              - limit: limite diario
              - remaining: mensagens restantes
              - warning: mensagem de aviso (ou None)
        """
        today = self._get_today()

        # Reseta se for um novo dia
        if user_id in self._usage and self._usage[user_id][0] != today:
            self._usage[user_id] = (today, 0)
        elif user_id not in self._usage:
            self._usage[user_id] = (today, 0)

        date_str, count = self._usage[user_id]
        count += 1
        self._usage[user_id] = (today, count)
        self._save()

        remaining = self.daily_limit - count
        warning = None

        if count >= self.daily_limit:
            warning = (
                "You've reached your daily practice limit! "
                "Come back tomorrow to continue learning. "
                "Keep up the great work! ⭐"
            )
        elif count >= int(self.daily_limit * 0.8):
            warning = (
                f"You've almost reached your daily practice limit! "
                f"You have {remaining} more messages today. "
                f"Great job practicing! 😊"
            )

        return {
            "allowed": True,
            "current": count,
            "limit": self.daily_limit,
            "remaining": remaining,
            "warning": warning,
        }

    def get_status(self, user_id: int) -> dict:
        """Retorna o status atual sem incrementar."""
        today = self._get_today()

        if user_id in self._usage and self._usage[user_id][0] == today:
            _, count = self._usage[user_id]
        else:
            count = 0

        remaining = max(0, self.daily_limit - count)

        return {
            "current": count,
            "limit": self.daily_limit,
            "remaining": remaining,
        }

    def reset_user(self, user_id: int) -> None:
        """Reseta o contador de um usuario."""
        self._usage.pop(user_id, None)
        self._save()
