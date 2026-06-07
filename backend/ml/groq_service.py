"""
Groq AI Service
===============
Uses Groq's ultra-fast LLM inference API for:
  - Career advice generation
  - Recommendation explanations
  - Resume feedback
  - Learning path suggestions

Default model: llama-3.3-70b-versatile (fast + highly capable)
"""

import httpx
import json
import re
from typing import List, Optional, Dict, Any
from loguru import logger


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqService:
    """Groq LLM API integration for AI-enhanced career features."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key  = api_key
        self.model    = model
        self.enabled  = bool(api_key and api_key not in ("", "your_groq_api_key_here"))

    # ─── Internal API call ────────────────────────────────────────────────────

    async def _call_api(self, prompt: str, max_tokens: int = 1024) -> str:
        """Send a prompt to Groq and return the text response."""
        if not self.enabled:
            return ""

        payload = {
            "model":       self.model,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": 0.7,
            "top_p":       0.9,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    GROQ_API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    # ─── Career Advice ────────────────────────────────────────────────────────

    async def get_career_advice(
        self,
        current_skills:   List[str],
        target_role:      str,
        experience_years: Optional[int] = None,
        education_level:  Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured, personalized career advice."""
        exp_str = f"{experience_years} years of experience" if experience_years else "unspecified experience"
        edu_str = education_level or "unspecified education"

        prompt = f"""You are an expert career advisor specializing in tech and AI/ML careers.

Profile:
- Current Skills: {', '.join(current_skills)}
- Target Role: {target_role}
- Experience: {exp_str}
- Education: {edu_str}

Provide comprehensive, actionable career advice. Respond ONLY with valid JSON (no markdown, no explanation outside JSON):
{{
  "advice": "2-3 paragraph personalized career advice",
  "action_items": ["specific action 1", "specific action 2", "specific action 3", "specific action 4", "specific action 5"],
  "timeline": "realistic timeline to achieve the goal",
  "resources": ["specific resource 1", "resource 2", "resource 3"]
}}"""

        try:
            text = await self._call_api(prompt, max_tokens=1000)
            json_str = self._extract_json(text)
            if json_str:
                data = json.loads(json_str)
                return {
                    "advice":       data.get("advice", text),
                    "action_items": data.get("action_items", []),
                    "timeline":     data.get("timeline", ""),
                    "resources":    data.get("resources", []),
                    "powered_by":   f"Groq AI · {self.model}",
                }
        except Exception as e:
            logger.warning(f"Groq career advice failed: {e}")

        return self._fallback_career_advice(current_skills, target_role)

    # ─── Recommendation Explanation ───────────────────────────────────────────

    async def explain_recommendation(
        self,
        course_title:     str,
        user_skills:      List[str],
        target_role:      Optional[str],
        similarity_score: float,
    ) -> str:
        """Generate a natural language explanation for a course recommendation."""
        prompt = f"""Explain in 2 concise sentences why "{course_title}" was recommended.

User skills: {', '.join(user_skills[:5])}
Target role: {target_role or 'not specified'}
Match score: {similarity_score:.2f}

Be encouraging and specific."""

        try:
            return await self._call_api(prompt, max_tokens=150)
        except Exception:
            return (
                f"This course aligns well with your skills in {', '.join(user_skills[:2])} "
                f"and helps you advance toward your goals."
            )

    # ─── AI Resume Skill Extraction ───────────────────────────────────────────

    async def extract_skills_from_resume_ai(self, resume_text: str, target_role: str = "") -> Dict[str, Any]:
        """Use Groq to intelligently extract and categorize skills from resume text."""
        role_hint = f" The user is targeting a {target_role} role." if target_role else ""

        prompt = f"""You are an expert technical recruiter.{role_hint}
Analyze this resume and extract all technical skills, tools, and technologies mentioned.

Resume:
{resume_text[:2000]}

Respond ONLY with valid JSON (no markdown):
{{
  "extracted_skills": ["skill1", "skill2", ...],
  "skill_categories": {{
    "Programming Languages": ["python", "java"],
    "Frameworks & Libraries": ["react", "tensorflow"],
    "Databases": ["mysql", "mongodb"],
    "Cloud & DevOps": ["aws", "docker"],
    "Data Science & ML": ["machine learning", "pandas"],
    "Other": ["agile", "git"]
  }},
  "experience_level": "Beginner|Intermediate|Advanced",
  "strengths": ["strength1", "strength2"],
  "suggested_roles": ["role1", "role2", "role3"]
}}"""

        try:
            text = await self._call_api(prompt, max_tokens=800)
            json_str = self._extract_json(text)
            if json_str:
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Groq resume extraction failed: {e}")
        return {}

    # ─── Resume Feedback ──────────────────────────────────────────────────────

    async def analyze_resume_feedback(self, resume_text: str, target_role: str) -> str:
        """Provide recruiter-style feedback on a resume for a target role."""
        prompt = f"""As a senior tech recruiter, give brief feedback on this resume for a {target_role} position.

Resume:
{resume_text[:1500]}

Provide 3-5 specific, actionable improvement suggestions as a numbered list."""

        try:
            return await self._call_api(prompt, max_tokens=500)
        except Exception:
            return "Unable to analyze resume at this time. Please check your Groq API key."

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract the first JSON object from a text response."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else None

    def _fallback_career_advice(self, skills: List[str], role: str) -> Dict:
        """Built-in fallback when Groq is unavailable."""
        return {
            "advice": (
                f"To become a {role}, focus on building a strong foundation in the core technical "
                f"skills required for the role. Start with courses that align with your existing "
                f"expertise in {', '.join(skills[:3])} and progressively advance to more specialized "
                f"topics. Build portfolio projects to demonstrate your skills practically."
            ),
            "action_items": [
                "Complete foundational courses in skills missing from your profile",
                "Build 2–3 portfolio projects that demonstrate key domain skills",
                "Contribute to open-source projects in your target area",
                "Network with professionals already working in the role",
                "Pursue relevant certifications to validate your expertise",
            ],
            "timeline": "6–12 months of dedicated learning and practice",
            "resources": [
                "GitHub — for portfolio projects and open-source contributions",
                "LinkedIn Learning — for structured professional development",
                "Kaggle — for hands-on data science practice",
                "LeetCode — for algorithmic problem solving",
            ],
            "powered_by": "Built-in Advisor (Groq AI unavailable)",
        }
