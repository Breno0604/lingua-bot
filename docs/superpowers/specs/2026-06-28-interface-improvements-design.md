# Interface Improvements (Buttons & Behavior) — Design Doc

**Date:** 2026-06-28
**Project:** LinguaBot (Telegram Bot)
**Status:** Implemented

## 1. Goal

Improve the Telegram inline keyboard interface by: (a) grouping Voice/Level config under a new Configuration button, (b) renaming action buttons and making them send new messages (not edit in-place), and (c) removing action buttons from previous messages when the user types something new.

## 2. Keyboard State Machine

The `conversation_buttons()` keyboard uses a 5-state model stored in `context.user_data["screen_type"]`:

| State | Visual |
|-------|--------|
| `conversation` (default) | `[➕ More Options] [⚙️ Configuration]` |
| `actions` | `[📝 Example] [📖 Explain] [🎯 Practice]` + `[◀ Hide Options]` |
| `config_menu` | `[🎤 Voice] [📊 Level]` + `[◀ Hide Options]` |
| `voice_picker` | Full voice selection keyboard (4 voices + speeds) + `[◀ Hide Options]` |
| `level_picker` | Full level selection keyboard (A1/A2/B1) + `[◀ Hide Options]` |

**Transitions:**
- `conversation` → "More Options" → `actions`
- `conversation` → "Configuration" → `config_menu`
- `config_menu` → "Voice" → `voice_picker`
- `config_menu` → "Level" → `level_picker`
- `voice_picker` → selects voice → save → `conversation`
- `level_picker` → selects level → save → `conversation`
- Any → "Hide Options" → `conversation`

## 3. Implementation Summary

### Files Modified

| File | Changes |
|------|---------|
| `bot/utils/keyboards.py` | Added `CONFIG_BUTTON`, renamed action buttons (More Examples→Example, etc.), added `config_menu_keyboard()`, `voice_picker_keyboard()`, `level_picker_keyboard()`, `cleanup_old_buttons()` |
| `bot/handlers/callbacks.py` | Added `_show_config_menu`, `_show_voice_picker`, `_show_level_picker` handlers; updated `_expand_options` to skip config states; `_collapse_options` returns to conversation; changed `_call_groq_for` to use `reply_text` (new message); `_set_voice`/`_set_level` return to collapsed when in config flow; `_set_speed` stays on voice_picker in config flow |
| `bot/handlers/message.py` | Added `cleanup_old_buttons` call before reply, track `button_msg_ids` after reply |
| `bot/handlers/audio.py` | Same cleanup + tracking pattern as message.py |
| `tests/test_callbacks.py` | Updated tests to assert `reply_text` instead of `edit_message_text` for action callbacks |

### Data Structures

`context.user_data` additions:
- `"button_msg_ids": list[int]` — message IDs of bot messages with action buttons
