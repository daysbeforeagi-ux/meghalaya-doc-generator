"""Orator — FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.db import init_db, purge_expired
from api.sessions import router as sessions_router
from api.intake import router as intake_router
from api.upload import router as upload_router
from api.generate import router as generate_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Fire-and-forget: purge sessions from previous runs
    await purge_expired()
    yield


app = FastAPI(
    title="Orator API",
    description="Government & institutional content studio — speech and press release generation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

SITE_ORIGIN = os.getenv("SITE_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[SITE_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router, prefix="/api")
app.include_router(intake_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(generate_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
