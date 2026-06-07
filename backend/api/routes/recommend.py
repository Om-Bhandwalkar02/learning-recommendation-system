"""
Recommendation API Routes
==========================
POST /api/v1/recommend      → Course recommendations
POST /api/v1/roadmap        → Learning roadmap generation
GET  /api/v1/courses        → Browse all courses
GET  /api/v1/courses/{id}   → Single course detail
GET  /api/v1/skills         → All available skills
GET  /api/v1/roles          → All supported target roles
"""

from fastapi import APIRouter, Request, HTTPException, Query
from loguru import logger
from typing import Optional, List
import time

from backend.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RoadmapRequest,
    LearningRoadmap,
    RoadmapPhase,
    CourseRecommendation,
    UserProfile,
    DifficultyLevel,
    SortBy,
)

router = APIRouter()


@router.post("/recommend", response_model=RecommendationResponse, summary="Get course recommendations")
async def get_recommendations(request: Request, payload: RecommendationRequest):
    """
    Generate personalized course recommendations based on user profile.
    
    **Request Body:**
    - `profile.current_skills`: List of your current skills
    - `profile.target_role`: Your target job role (optional)
    - `profile.preferred_difficulty`: Beginner / Intermediate / Advanced / All
    - `profile.n_recommendations`: Number of courses to return (1-20)
    
    **Returns:** Ranked list of courses with similarity scores and explanations.
    """
    engine = request.app.state.engine
    profile = payload.profile

    try:
        results, elapsed = engine.recommend(
            current_skills=profile.current_skills,
            target_role=profile.target_role,
            preferred_difficulty=profile.preferred_difficulty.value,
            preferred_categories=profile.preferred_categories,
            completed_courses=profile.completed_courses or [],
            max_duration_hours=profile.max_duration_hours,
            free_only=profile.free_only,
            n=profile.n_recommendations,
            sort_by=payload.sort_by.value,
        )

        # Convert to Pydantic models
        recommendations = []
        for r in results:
            try:
                recommendations.append(CourseRecommendation(**r))
            except Exception as e:
                logger.warning(f"Skipping malformed course entry: {e}")

        return RecommendationResponse(
            success=True,
            query_skills=profile.current_skills,
            target_role=profile.target_role,
            total_courses_analyzed=engine.course_count,
            recommendations=recommendations,
            processing_time_ms=round(elapsed, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post("/roadmap", summary="Generate learning roadmap")
async def generate_roadmap(request: Request, payload: RoadmapRequest):
    """
    Generate a phased learning roadmap toward a target role.
    
    Returns a structured plan with phases, courses per phase, and milestones.
    """
    engine = request.app.state.engine
    try:
        roadmap = engine.generate_roadmap(
            current_skills=payload.current_skills,
            target_role=payload.target_role,
            timeframe_months=payload.timeframe_months,
        )
        return {"success": True, **roadmap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses", summary="Browse all courses")
async def get_courses(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    free_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Browse and filter the course catalog."""
    engine = request.app.state.engine
    df = engine.df.copy()

    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if difficulty:
        df = df[df["difficulty"].str.lower() == difficulty.lower()]
    if platform:
        df = df[df["platform"].str.lower() == platform.lower()]
    if free_only:
        df = df[df["price_usd"] == 0]

    total = len(df)
    page = df.iloc[offset: offset + limit]

    courses = []
    for _, row in page.iterrows():
        courses.append(engine._row_to_dict(row))

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "courses": courses,
    }


@router.get("/courses/{course_id}", summary="Get course by ID")
async def get_course(request: Request, course_id: str):
    """Get full details for a specific course by its ID."""
    engine = request.app.state.engine
    row = engine.df[engine.df["course_id"] == course_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    return {"success": True, "course": engine._row_to_dict(row.iloc[0])}


@router.get("/skills", summary="List all available skills")
async def get_skills(request: Request):
    """Return all unique skills in the dataset."""
    engine = request.app.state.engine
    return {"success": True, "skills": engine.get_all_skills()}


@router.get("/categories", summary="List all categories")
async def get_categories(request: Request):
    """Return all unique course categories."""
    engine = request.app.state.engine
    return {"success": True, "categories": engine.get_all_categories()}


@router.get("/roles", summary="List supported target roles")
async def get_roles(request: Request):
    """Return all job roles supported for skill gap and roadmap analysis."""
    engine = request.app.state.engine
    return {"success": True, "roles": engine.get_all_roles()}
