"""
Data Models Module
Pydantic schemas for API request/response validation and serialization.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class DifficultyLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    ALL = "All"


class SortBy(str, Enum):
    SCORE = "score"
    RATING = "rating"
    ENROLLED = "enrolled"
    DURATION = "duration"


# ─── Course Model ─────────────────────────────────────────────────────────────

class Course(BaseModel):
    """Represents a single course from the dataset."""
    course_id: str
    title: str
    platform: str
    provider: str
    category: str
    subcategory: str
    skills: List[str]
    difficulty: str
    duration_hours: float
    rating: float
    enrolled: int
    price_usd: float
    certificate: bool
    description: str
    url_slug: str
    prerequisites: List[str]
    learning_outcomes: str
    
    model_config = ConfigDict(from_attributes=True)


class CourseRecommendation(Course):
    """Course with recommendation score and explanation."""
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")
    recommendation_score: float = Field(..., ge=0, le=100, description="Final weighted score 0-100")
    match_reasons: List[str] = Field(default=[], description="Why this course was recommended")
    skill_overlap: List[str] = Field(default=[], description="Overlapping skills with user profile")
    rank: int = Field(..., ge=1, description="Recommendation rank")


# ─── Request Models ───────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """User profile for generating recommendations."""
    current_skills: List[str] = Field(
        ...,
        min_length=1,
        description="List of skills the user currently has",
        examples=[["python", "machine learning", "numpy"]]
    )
    target_role: Optional[str] = Field(
        None,
        description="Career goal or target job role",
        examples=["Data Scientist", "ML Engineer"]
    )
    preferred_difficulty: DifficultyLevel = Field(
        DifficultyLevel.ALL,
        description="Preferred course difficulty"
    )
    preferred_categories: Optional[List[str]] = Field(
        None,
        description="Preferred course categories"
    )
    completed_courses: Optional[List[str]] = Field(
        default=[],
        description="Course IDs already completed"
    )
    max_duration_hours: Optional[float] = Field(
        None,
        ge=1,
        description="Maximum acceptable course duration in hours"
    )
    free_only: bool = Field(False, description="Only show free courses")
    n_recommendations: int = Field(
        10,
        ge=1,
        le=20,
        description="Number of recommendations to return"
    )

    @field_validator("current_skills")
    @classmethod
    def normalize_skills(cls, v):
        """Normalize skill strings to lowercase stripped."""
        return [skill.strip().lower() for skill in v if skill.strip()]


class RecommendationRequest(BaseModel):
    """Full recommendation request payload."""
    profile: UserProfile
    sort_by: SortBy = SortBy.SCORE
    include_explanations: bool = True


class SkillGapRequest(BaseModel):
    """Request for skill gap analysis."""
    current_skills: List[str] = Field(..., min_length=1)
    target_role: str = Field(..., min_length=2, description="Target job role")

    @field_validator("current_skills")
    @classmethod
    def normalize_skills(cls, v):
        return [s.strip().lower() for s in v if s.strip()]


class RoadmapRequest(BaseModel):
    """Request for learning roadmap generation."""
    current_skills: List[str] = Field(..., min_length=1)
    target_role: str = Field(..., min_length=2)
    timeframe_months: int = Field(6, ge=1, le=24, description="Target completion timeframe")

    @field_validator("current_skills")
    @classmethod
    def normalize_skills(cls, v):
        return [s.strip().lower() for s in v if s.strip()]


class ResumeAnalyzeRequest(BaseModel):
    """Request to analyze resume text for skills."""
    resume_text: str = Field(..., min_length=50, description="Plain text content of the resume")
    target_role: Optional[str] = None


class CareerAdviceRequest(BaseModel):
    """Request for Gemini career advice."""
    current_skills: List[str]
    target_role: str
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    education_level: Optional[str] = None


# ─── Response Models ──────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    """Full recommendation API response."""
    success: bool = True
    query_skills: List[str]
    target_role: Optional[str]
    total_courses_analyzed: int
    recommendations: List[CourseRecommendation]
    processing_time_ms: float


class SkillGapAnalysis(BaseModel):
    """Skill gap analysis results."""
    target_role: str
    current_skills: List[str]
    required_skills: List[str]
    missing_skills: List[str]
    proficiency_skills: List[str]   # Skills user has that are relevant
    gap_percentage: float            # Percentage of required skills missing
    priority_skills: List[str]       # Top skills to learn first
    recommended_courses: List[CourseRecommendation]


class RoadmapPhase(BaseModel):
    """A single phase in the learning roadmap."""
    phase_number: int
    title: str
    duration_weeks: int
    description: str
    skills_to_learn: List[str]
    courses: List[CourseRecommendation]
    milestone: str


class LearningRoadmap(BaseModel):
    """Complete learning roadmap response."""
    target_role: str
    total_duration_months: int
    overview: str
    phases: List[RoadmapPhase]
    total_courses: int
    estimated_hours: float


class ResumeAnalysis(BaseModel):
    """Resume analysis results."""
    extracted_skills: List[str]
    skill_categories: Dict[str, List[str]]
    skill_strength_score: float
    recommendations: List[CourseRecommendation]
    suggested_roles: List[str]
    missing_skills_for_target: Optional[List[str]] = None


class CareerAdviceResponse(BaseModel):
    """Gemini career advice response."""
    advice: str
    action_items: List[str]
    timeline: str
    resources: List[str]
    powered_by: str = "Gemini AI"


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    dataset_loaded: bool
    total_courses: int
    ml_model_ready: bool
    gemini_enabled: bool


class StatsResponse(BaseModel):
    """Dataset statistics response."""
    total_courses: int
    platforms: Dict[str, int]
    categories: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    average_rating: float
    skill_count: int
    top_skills: List[Dict[str, Any]]
