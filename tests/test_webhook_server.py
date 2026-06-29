"""
LinguaBot --- Tests for bot.webhook_server

Tests the FastAPI webhook server endpoints:
  - GET /health
  - POST /webhook
  - Startup and shutdown events
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_application():
    """Cria um mock do PTB Application para testes."""
    app = MagicMock()
    bot = MagicMock()
    bot.username = "TestLinguaBot"
    bot.get_webhook_info = AsyncMock()
    bot.get_webhook_info.return_value = MagicMock(
        url="https://example.com/webhook",
        pending_update_count=0,
    )
    bot.set_webhook = AsyncMock()
    app.bot = bot
    config = MagicMock()
    config.render_url = "https://example.com"
    app.bot_data = {"config": config}
    app.process_update = AsyncMock()
    app.initialize = AsyncMock()
    app.shutdown = AsyncMock()
    return app


@pytest.fixture
def patched_module(mock_application):
    """Substitui a variavel global application no modulo webhook_server."""
    import bot.webhook_server as ws
    original = ws.application
    ws.application = mock_application
    yield ws
    ws.application = original


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(patched_module, mock_application):
    """GET /health returns status ok with service info."""
    transport = ASGITransport(app=patched_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "lingua-bot"


@pytest.mark.asyncio
async def test_health_endpoint_no_bot(patched_module):
    """GET /health returns ok even without bot initialized."""
    patched_module.application.bot = None
    transport = ASGITransport(app=patched_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_endpoint_success(patched_module, mock_application):
    """POST /webhook with valid data returns 200."""
    import bot.webhook_server as ws
    # Configurar Update.de_json para retornar um MagicMock
    with patch.object(ws, "Update") as mock_update_cls:
        mock_update = MagicMock()
        mock_update_cls.de_json.return_value = mock_update

        transport = ASGITransport(app=patched_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook", json={"update_id": 1})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    mock_application.process_update.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_endpoint_no_bot(patched_module):
    """POST /webhook without bot returns 503."""
    patched_module.application.bot = None
    transport = ASGITransport(app=patched_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json={"update_id": 1})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_webhook_endpoint_invalid_json(patched_module):
    """POST /webhook with invalid payload returns 200 or 500."""
    transport = ASGITransport(app=patched_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json={"invalid": "data"})
    assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_startup_sets_webhook(patched_module, mock_application):
    """Startup event initializes bot and sets webhook."""
    await patched_module.startup()
    mock_application.initialize.assert_called_once()
    mock_application.bot.set_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_startup_no_render_url(patched_module, mock_application):
    """Startup without RENDER_URL logs error but does not crash."""
    mock_application.bot_data["config"].render_url = ""
    await patched_module.startup()
    mock_application.bot.set_webhook.assert_not_called()


@pytest.mark.asyncio
async def test_shutdown_calls_shutdown(patched_module, mock_application):
    """Shutdown event calls application.shutdown."""
    await patched_module.shutdown()
    mock_application.shutdown.assert_called_once()
