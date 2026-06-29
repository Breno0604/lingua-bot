# Contributing to LinguaBot

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Breno0604/lingua-bot.git
   cd lingua-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio httpx  # dev dependencies
   ```

4. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

## Code Style

- Use `from __future__ import annotations` at the top of all Python files
- Use modern typing syntax: `str | None` instead of `Optional[str]`
- Follow the existing layered architecture pattern
- Write docstrings in English for all public methods
- Keep handlers thin; extract business logic to services

## Testing

- All tests are in the `tests/` directory
- Run tests with: `python -m pytest tests/ -v`
- Run with coverage: `python -m pytest tests/ --cov=bot --cov-report=term-missing`
- Write tests for all new features using pytest + AsyncMock
- Use fixtures from `conftest.py` (mock_update, configured_context, etc.)

## Project Structure

```
bot/
  handlers/     # Telegram update handlers
  services/     # Business logic (Groq, TTS, Level, etc.)
  utils/        # Utilities (formatting, keyboards, rate limiter)
  constants.py  # Centralized constants
  typing.py     # Type aliases
  database.py   # Database abstraction
  main.py       # Bot entry point
  config.py     # Environment config
tests/          # Test files
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for your changes
3. Ensure all existing tests pass
4. Update documentation if needed
5. Submit a PR with a clear description

## Commit Messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `refactor:` code change without feature/fix
- `test:` adding or updating tests
- `docs:` documentation changes
- `chore:` maintenance tasks
