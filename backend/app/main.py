"""
StudentsAI MVP - FastAPI Backend Application
"""

import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    ask,
    auth,
    concepts,
    courses,
    documents,
    flashcards,
    graph,
    health,
    notes,
    practice,
    profile,
    today,
    uploads,
)
from app.api import settings as settings_api
from app.api.uploads import UPLOAD_DIR
from app.config import ALLOWED_ORIGINS, DEBUG, HOST, PORT, settings
from app.db.session import create_tables

CORS_ORIGIN_PATTERN = r"https://([a-zA-Z0-9-]+\.)?(studentsai\.org|vercel\.app)$"
ROUTERS = (
    courses,
    concepts,
    practice,
    ask,
    today,
    documents,
    health,
    auth,
    notes,
    flashcards,
    graph,
    profile,
    uploads,
    settings_api,
)


def _origin_variants(url: str) -> list[str]:
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return []
        base = f"{p.scheme}://{p.netloc}"
        hosts = {base}
        host = p.netloc
        if host.startswith("www."):
            hosts.add(f"{p.scheme}://{host[4:]}")
        else:
            hosts.add(f"{p.scheme}://www.{host}")
        return list(hosts)
    except Exception:
        return []


def _allowed_origins() -> list[str]:
    """BACKEND_CORS_ORIGINS, the comma-separated allowed_origins, and FRONTEND_URL with and without www."""
    origins_set = set()
    for o in ALLOWED_ORIGINS:
        o = o.strip()
        if o:
            origins_set.add(o)
    for o in (settings.allowed_origins or "").split(","):
        o = o.strip()
        if o:
            origins_set.add(o)
    for v in _origin_variants(settings.frontend_url):
        origins_set.add(v)
    return list(origins_set)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    yield


async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if DEBUG else None,
        },
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="StudentsAI MVP API",
        description="AI-powered study assistant API",
        version="1.0.0",
        docs_url="/docs" if DEBUG else None,
        redoc_url="/redoc" if DEBUG else None,
        lifespan=lifespan,
    )

    allowed_origins = _allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=CORS_ORIGIN_PATTERN,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Extra safety: ensure CORS headers are present on all responses when Origin matches
    cors_regex = re.compile(CORS_ORIGIN_PATTERN)

    @app.middleware("http")
    async def ensure_cors_headers(request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and (origin in allowed_origins or cors_regex.match(origin)):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    app.add_exception_handler(Exception, global_exception_handler)

    # Serve uploaded files (development convenience)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    for router_module in ROUTERS:
        app.include_router(router_module.router)

    return app


app = create_app()


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
