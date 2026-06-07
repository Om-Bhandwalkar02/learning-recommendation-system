"""
Admin API Routes
=================
GET /api/v1/health   → System health check
GET /api/v1/stats    → Dataset statistics
"""

from fastapi import APIRouter, Request
from backend.core.config import get_settings

router   = APIRouter()
settings = get_settings()


@router.get("/health", summary="Health check")
async def health_check(request: Request):
    """Check if the system is healthy and all components are ready."""
    engine = request.app.state.engine
    ai     = request.app.state.ai
    return {
        "status":         "healthy",
        "version":        settings.APP_VERSION,
        "dataset_loaded": engine.is_ready,
        "total_courses":  engine.course_count,
        "ml_model_ready": engine.is_ready,
        "gemini_enabled": ai.enabled,   # kept as gemini_enabled for frontend compatibility
        "ai_provider":    "Groq",
        "ai_model":       settings.GROQ_MODEL,
    }


@router.get("/stats", summary="Dataset statistics")
async def get_stats(request: Request):
    """Return detailed statistics about the course dataset."""
    engine = request.app.state.engine
    return {"success": True, **engine.get_statistics()}
