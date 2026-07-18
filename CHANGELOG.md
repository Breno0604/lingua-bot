# Changelog

All notable changes to LinguaBot will be documented in this file.

## [Unreleased]

### Added
- `ResponseValidator` service for post-generation response validation
- Level-specific parameters (temperature, top_p, max_tokens) for A1, A2, B1
- Frequency and presence penalties to reduce repetition
- Few-shot examples in system prompts
- Anti-repetition structure rules
- Data files: `top_800_words.txt`, `idioms_to_avoid.txt`

### Changed
- Improved system prompts with better correction rules
- Response validation integrated into GroqService with retry logic

### Fixed
- Responses now stay within level-appropriate word limits
- Vocabulary validation for A1 level (800 most common words)

## [1.0.0] - 2026-06-28

### Added
- Initial release of LinguaBot (formerly english-teacher-bot)
- Telegram bot with LLM-powered English conversation using Groq (llama-3.3-70b-versatile)
- Level adaptation system (A1, A2, B1) with distinct system prompts
- Vocabulary tracking with automatic extraction from Groq replies
- 15 conversation topics for guided practice
- Speech-to-Text via Deepgram nova-2 model
- Text-to-Speech via Deepgram Aura (4 voices) with ElevenLabs fallback
- Audio caching and speed control
- Inline button UI with expand/collapse pattern
- Rate limiter with daily limits and warnings
- Configuration menu (voice, speed, level selection)
- SQLite database (development) and Supabase (production)
- Webhook server via FastAPI for Render deployment
- 100+ unit tests with pytest

### Architecture
- Layered architecture: handlers -> services -> database
- Dependency injection via PTB bot_data
- TTSOrchestrator pattern for primary/fallback TTS coordination
