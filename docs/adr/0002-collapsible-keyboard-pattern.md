# ADR 0002: Collapsible Inline Keyboard Pattern

## Status

Accepted (2026-06-15)

## Context

The bot's inline keyboards were growing complex. After each response, users saw 3-4 action buttons (More Examples, Explain, Practice, Config). This cluttered the chat and made the conversation harder to read.

## Decision

Implement a collapsible keyboard pattern:

- **Default state**: Single button `+ More Options` is shown after each response
- **Expanded state**: All action buttons are visible with a `Hide Options` button
- **Config menu**: Has its own collapse behavior within the configuration flow
- **Special cases**: Vocab pagination stays expanded during navigation; topic suggestions are always visible

The pattern was implemented via:
- `collapse_keyboard()` function in `keyboards.py` that wraps any keyboard with expand/collapse
- `_set_screen_type()` helper tracks the current screen for context-aware expansion
- `cleanup_old_buttons()` removes buttons from previous bot messages to reduce visual noise

## Consequences

- Significantly cleaner chat appearance
- Users discover more features through the expand interaction
- Additional development complexity in tracking screen state
- Voice messages required special handling (Telegram can't edit voice message text)
