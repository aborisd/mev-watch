from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..db import close_pool, init_pool
from ..logging import configure_logging, get_logger
from .routes import router

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_pool(min_size=2, max_size=16)
    log.info("api_start", host=settings.api_host, port=settings.api_port)
    yield
    await close_pool()
    log.info("api_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MEV-Watch API",
        version="0.1.0",
        description="Real-time MEV detection on Ethereum — sandwich + JIT.",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
