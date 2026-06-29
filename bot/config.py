"""
LinguaBot --- Configuration Module
Carrega e valida variaveis de ambiente para o bot.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    """Carrega variaveis de um arquivo .env para o ambiente."""
    env_path = Path(path)
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'").strip()
            if key:
                os.environ.setdefault(key, val)


@dataclass
class Config:
    # Telegram
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))

    # Groq (substitui Gemini)
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Modo de operacao
    bot_mode: str = os.getenv("BOT_MODE", "polling")  # "polling" ou "webhook"

    # Render / Webhook
    render_url: str = os.getenv("RENDER_URL", "")

    # Supabase (producao)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")

    # Deepgram (pos-MVP)
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")

    # ElevenLabs (pos-MVP)
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Limites
    daily_limit: int = int(os.getenv("DAILY_LIMIT", "100"))
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "15"))


def load_config() -> Config:
    """Carrega e valida a configuracao."""
    _load_dotenv()  # Carrega .env antes de ler as variaveis
    cfg = Config()

    # Validacoes essenciais
    errors = []
    if not cfg.bot_token:
        errors.append("BOT_TOKEN nao definido no .env")
    if not cfg.groq_api_key:
        errors.append("GROQ_API_KEY nao definido no .env")

    if errors:
        raise ValueError(
            "Erros de configuracao:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return cfg
