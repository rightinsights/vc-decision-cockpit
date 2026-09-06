"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import agent, analysis, changes, companies, decisions, notes, thesis
from .config import get_settings
from .db import SessionLocal, init_db
from .seed import seed_thesis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_thesis(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="VC Decision Cockpit", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(thesis.router)
    app.include_router(companies.router)
    app.include_router(analysis.router)
    app.include_router(decisions.router)
    app.include_router(agent.router)
    app.include_router(changes.router)
    app.include_router(notes.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
