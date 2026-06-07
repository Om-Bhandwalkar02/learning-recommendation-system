"""
Learning Recommendation System — FastAPI Application
======================================================
Main entry point. Initializes the app, registers routes,
loads the ML engine on startup.
"""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Force-load .env before any settings are imported
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from loguru import logger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.core.config import get_settings
from backend.ml.engine import RecommendationEngine
from backend.ml.groq_service import GroqService
from backend.api.routes import recommend, analyze, admin

# ─── Load Settings (cache cleared so .env values are picked up) ───────────────
get_settings.cache_clear()
settings = get_settings()

# ─── Global Singletons ────────────────────────────────────────────────────────
engine: RecommendationEngine = None
ai:     GroqService          = None


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ML engine and AI service on startup; clean up on shutdown."""
    global engine, ai

    logger.info("🚀 Starting Learning Recommendation System...")

    # Recommendation engine
    engine = RecommendationEngine(settings.DATASET_PATH)
    engine.initialize()

    # Groq AI service
    ai = GroqService(settings.GROQ_API_KEY, settings.GROQ_MODEL)
    if ai.enabled:
        logger.success(f"✅ Groq AI enabled — model: {settings.GROQ_MODEL}")
    else:
        logger.info("ℹ️  Groq AI disabled (no API key configured)")

    # Make singletons available to routes
    app.state.engine = engine
    app.state.ai     = ai

    logger.success(f"✅ Server ready at http://{settings.HOST}:{settings.PORT}")
    yield

    logger.info("Shutting down...")


# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{duration:.2f}ms"
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(recommend.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(analyze.router,   prefix="/api/v1", tags=["Analysis"])
app.include_router(admin.router,     prefix="/api/v1", tags=["Admin"])

# ─── Static Frontend ──────────────────────────────────────────────────────────
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend/assets"), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse("frontend/index.html")


# ─── Global Error Handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "Internal server error", "error": str(exc)},
    )


# ─── Run directly ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
