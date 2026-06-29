from __future__ import annotations

# ── Level System ──

VALID_LEVELS: list[str] = ["A1", "A2", "B1"]

LEVEL_LABELS: dict[str, str] = {
    "A1": "A1 - Iniciante",
    "A2": "A2 - B\u00e1sico",
    "B1": "B1 - Intermedi\u00e1rio",
}

LEVEL_CONFIRMATIONS: dict[str, str] = {
    "A1": (
        "I'll use very simple words and short sentences. "
        "Let's start practicing! \U0001f680"
    ),
    "A2": (
        "I'll use everyday vocabulary and slightly longer sentences now. "
        "You're doing great! \U0001f31f"
    ),
    "B1": (
        "I'll use more varied vocabulary and natural expressions. "
        "Let's have a real conversation! \U0001f44d"
    ),
}

DEFAULT_LEVEL: str = "A1"

# ── TTS / Audio ──

SPEED_OPTIONS: list[float] = [0.75, 0.85, 1.0, 1.15, 1.25]

DEFAULT_SPEED_BY_LEVEL: dict[str, float] = {
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
}

DEFAULT_VOICE_ID: str = "aura-2-thalia-en"

DEEPGRAM_MAX_TEXT_CHARS: int = 150
ELEVENLABS_MAX_TEXT_CHARS: int = 100

DEEPGRAM_VOICES: list[tuple[str, str, str]] = [
    ("aura-2-thalia-en", "Thalia", "Feminine, clear, confident, energetic"),
    ("aura-2-odysseus-en", "Odysseus", "Masculine, calm, smooth, professional"),
    ("aura-2-helena-en", "Helena", "Feminine, caring, natural, friendly"),
    ("aura-2-mars-en", "Mars", "Masculine, smooth, patient, trustworthy, baritone"),
]

SPEED_LABELS: dict[float, str] = {
    0.75: "\U0001f422 Very slow",
    0.85: "Slow",
    1.0: "Normal",
    1.15: "Fast",
    1.25: "\U0001f407 Very fast",
}

# ── Limits ──

DEFAULT_DAILY_LIMIT: int = 100
DEFAULT_MAX_HISTORY_TURNS: int = 15

# ── Database ──

VOCAB_PAGE_SIZE: int = 10

# ── Telegram ──

TELEGRAM_MAX_MESSAGE_LENGTH: int = 4000
