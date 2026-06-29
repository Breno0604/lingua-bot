import re
from typing import Optional


EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def clean_text(text: str) -> str:
    """Remove emojis que TTS tentaria pronunciar."""
    return EMOJI_PATTERN.sub("", text).strip()


def truncate_text(text: str, max_chars: int = 150) -> str:
    """Trunca o texto mantendo a frase completa."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars // 2:
        return truncated[: last_period + 1].strip()

    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        return truncated[:last_space].strip() + "."

    return truncated.strip() + "."
