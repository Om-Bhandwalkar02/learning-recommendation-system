"""
Analysis API Routes
====================
POST /api/v1/skill-gap       → Skill gap analysis
POST /api/v1/resume-analyze  → Resume skill extraction
POST /api/v1/career-advice   → Groq AI career advice
"""

from fastapi import APIRouter, Request, HTTPException
from loguru import logger
from backend.models.schemas import (
    SkillGapRequest,
    ResumeAnalyzeRequest,
    CareerAdviceRequest,
    CourseRecommendation,
)
from backend.ml.resume_analyzer import (
    extract_skills_from_resume,
    calculate_skill_strength,
    suggest_roles,
)

router = APIRouter()


@router.post("/skill-gap", summary="Analyze skill gap for a target role")
async def skill_gap_analysis(request: Request, payload: SkillGapRequest):
    """
    Analyze the gap between your current skills and a target job role.

    Returns required skills, skills you have, missing skills,
    priority learning order, and recommended courses.
    """
    engine = request.app.state.engine
    try:
        result = engine.analyze_skill_gap(
            current_skills=payload.current_skills,
            target_role=payload.target_role,
        )

        courses = []
        for c in result.get("recommended_courses", []):
            try:
                courses.append(CourseRecommendation(**c))
            except Exception as e:
                logger.warning(f"Skipping malformed course in skill-gap: {e}")
        result["recommended_courses"] = [c.model_dump() for c in courses]

        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-analyze", summary="Analyze resume to extract skills")
async def resume_analysis(request: Request, payload: ResumeAnalyzeRequest):
    """
    Extract skills from resume text using Groq AI (if enabled) or keyword matching.
    Returns skill categories, suggested roles, gap analysis, and recommended courses.
    """
    engine = request.app.state.engine
    ai     = request.app.state.ai

    try:
        ai_powered = False
        skills, categorized, suggested_roles, strengths = [], {}, [], []

        # ── Try Groq AI extraction first ──────────────────────────────────────
        if ai.enabled:
            try:
                ai_result = await ai.extract_skills_from_resume_ai(
                    payload.resume_text, payload.target_role or ""
                )
                if ai_result and ai_result.get("extracted_skills"):
                    skills         = ai_result.get("extracted_skills", [])
                    categorized    = ai_result.get("skill_categories", {})
                    suggested_roles = ai_result.get("suggested_roles", [])
                    strengths      = ai_result.get("strengths", [])
                    ai_powered     = True
            except Exception as e:
                logger.warning(f"Groq resume extraction failed, falling back: {e}")

        # ── Fallback to keyword matching ──────────────────────────────────────
        if not ai_powered:
            skills, categorized = extract_skills_from_resume(payload.resume_text)
            suggested_roles     = suggest_roles(skills)

        strength       = calculate_skill_strength(skills, categorized)
        recs           = []
        missing_skills = None

        if skills:
            raw_recs, _ = engine.recommend(
                current_skills=skills,
                target_role=payload.target_role,
                n=8,
            )
            for r in raw_recs:
                try:
                    recs.append(CourseRecommendation(**r).model_dump())
                except Exception as e:
                    logger.warning(f"Skipping malformed course in resume-analyze: {e}")

            if payload.target_role:
                gap = engine.analyze_skill_gap(skills, payload.target_role)
                missing_skills = gap.get("missing_skills", [])

        return {
            "success":                   True,
            "ai_powered":                ai_powered,
            "extracted_skills":          skills,
            "skill_categories":          categorized,
            "skill_strength_score":      strength,
            "suggested_roles":           suggested_roles,
            "strengths":                 strengths,
            "missing_skills_for_target": missing_skills,
            "recommendations":           recs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", summary="AI explanation for a course recommendation")
async def explain_recommendation(request: Request, payload: dict):
    """
    Get a 2-sentence AI explanation of why a course was recommended.
    Body: { course_title, user_skills, target_role, similarity_score }
    """
    ai = request.app.state.ai
    try:
        explanation = await ai.explain_recommendation(
            course_title=payload.get("course_title", ""),
            user_skills=payload.get("user_skills", []),
            target_role=payload.get("target_role"),
            similarity_score=float(payload.get("similarity_score", 0.5)),
        )
        return {"success": True, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/career-advice", summary="Get AI career advice (Groq)")
async def career_advice(request: Request, payload: CareerAdviceRequest):
    """
    Get personalized AI-powered career advice using Groq LLM.

    Falls back to built-in advice if Groq is unavailable.
    """
    ai = request.app.state.ai
    try:
        advice = await ai.get_career_advice(
            current_skills=payload.current_skills,
            target_role=payload.target_role,
            experience_years=payload.experience_years,
            education_level=payload.education_level,
        )
        return {"success": True, **advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
