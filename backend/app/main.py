from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import token_payload_or_none
from app.db import engine, init_db, AsyncSessionLocal
from app.routers import auth, clients, limits, positions, pricing, rfq, trades
from app.seed import ensure_seed_data
from app.services.market_data import market_data_service
from app.services.ws import ALLOWED_CHANNELS, manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_seed_data(db)
    await market_data_service.start()
    try:
        yield
    finally:
        await market_data_service.stop()
        await engine.dispose()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(rfq.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(positions.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(limits.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/{channel}")
async def websocket_channel(websocket: WebSocket, channel: str) -> None:
    if channel not in ALLOWED_CHANNELS:
        await websocket.close(code=1008)
        return

    token = websocket.query_params.get("token", "")
    payload = token_payload_or_none(token)
    if not payload:
        await websocket.close(code=1008)
        return

    await manager.connect(channel, websocket)

    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({"channel": channel, "type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(channel, websocket)
