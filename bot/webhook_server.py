"""
LinguaBot --- Webhook Server (FastAPI)

Servidor HTTP usado para modo webhook no Render.
Fornece:
  - POST /webhook: endpoint para o Telegram enviar updates
  - GET /health: health check para monitoramento

Reusa build_application() de main.py para evitar duplicacao
de registro de handlers.

Modo de uso:
  Render: uvicorn bot.webhook_server:app --host 0.0.0.0 --port $PORT
  Local:  uvicorn bot.webhook_server:app --host 0.0.0.0 --port 8000

  $PORT e uma variavel definida automaticamente pelo Render.
  Localmente, use uma porta fixa (ex: 8000).
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update

from bot.main import build_application

logger = logging.getLogger(__name__)

# --- Inicializacao (reusa build_application de main.py) ---
application = build_application()

# --- FastAPI App ---
app = FastAPI(title="LinguaBot Webhook")


@app.on_event("startup")
async def startup():
    """Inicializa o application do PTB e configura o webhook no Telegram."""
    logger.info("Inicializando LinguaBot em modo WEBHOOK...")

    config = application.bot_data["config"]
    if not config.render_url:
        logger.error("RENDER_URL nao configurada! Webhook nao pode ser registrado.")
        return

    await application.initialize()

    webhook_url = f"{config.render_url.rstrip('/')}/webhook"
    await application.bot.set_webhook(url=webhook_url)

    webhook_info = await application.bot.get_webhook_info()
    logger.info("Webhook configurado: %s | Pendente: %s",
                webhook_info.url, webhook_info.pending_update_count)


@app.on_event("shutdown")
async def shutdown():
    """Finaliza o application do PTB."""
    logger.info("Encerrando LinguaBot...")
    await application.shutdown()


@app.get("/health")
async def health_check():
    """Health check endpoint para monitoramento do Render."""
    webhook_info = None
    try:
        if application.bot:
            webhook_info = await application.bot.get_webhook_info()
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "lingua-bot",
        "webhook_url": webhook_info.url if webhook_info else None,
        "pending_updates": webhook_info.pending_update_count if webhook_info else None,
        "bot_username": application.bot.username if application.bot else None,
    }


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Endpoint para receber updates do Telegram via webhook.

    Recebe o JSON do Telegram, cria um objeto Update
    e o processa usando o Application do python-telegram-bot.
    """
    try:
        data = await request.json()

        if not application.bot:
            logger.error("Application nao inicializado!")
            return JSONResponse(
                content={"ok": False, "error": "Application not initialized"},
                status_code=503,
            )

        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error("Erro ao processar webhook: %s", e)
        return JSONResponse(
            content={"ok": False, "error": str(e)},
            status_code=500,
        )


if __name__ == "__main__":
    """Permite rodar com 'python bot/webhook_server.py' (fallback local)."""
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    print(f"Iniciando servidor local na porta {port}...")
    print(f"Health check: http://localhost:{port}/health")
    uvicorn.run("bot.webhook_server:app", host="0.0.0.0", port=port)
