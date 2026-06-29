from __future__ import annotations

from typing import TypedDict

UserLevel = str
VoiceId = str
SpeedOption = float
UserId = int
ScreenType = str


class RateLimitResult(TypedDict):
    allowed: bool
    current: int
    limit: int
    remaining: int
    warning: str | None


class VocabDict(TypedDict):
    word: str
    translation: str
    context: str
