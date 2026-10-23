"""
WattWise FastAPI Application
==============================
Entry point: uvicorn backend.main:app --reload

The app serves:
  /api/*         — REST API endpoints
  /docs          — Swagger UI (auto-generated)
  /              — Static frontend (frontend/ directory)
"""

import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path so utils.py etc. are importable
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.routers import auth, users, energy, ml, admin


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    from backend.services.ml_service import _load_model
    _load_model()
    print(f"[App] WattWise API ready. Visit http://localhost:8000/docs")
    yield
    # Shutdown (nothing to clean up)

# ── App creation ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    description=(
        "WattWise — ML-Based Campus Energy Waste Detection & Analytics API. "
        "All campus telemetry is simulated for local development. "
        "See /docs for interactive API documentation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(energy.router)
app.include_router(ml.router)
app.include_router(admin.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "SQLite (local)",
        "note": "Campus telemetry is simulated for local development.",
    }


# ── Global exception handler (no stack traces in responses) ──────────────────
@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    import logging
    logging.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ── Serve the existing frontend as static files ───────────────────────────────
_frontend_dir = _ROOT / "frontend"
if _frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="frontend",
    )
    print(f"[App] Frontend served from {_frontend_dir}")
