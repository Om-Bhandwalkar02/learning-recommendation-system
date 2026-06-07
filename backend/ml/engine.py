"""
ML Recommendation Engine
=========================
Core engine using TF-IDF vectorization and Cosine Similarity.

Architecture:
  1. Data Loading & Preprocessing  → Clean and normalize course data
  2. Feature Engineering           → Build rich text features per course
  3. TF-IDF Vectorization          → Convert text features to TF-IDF matrix
  4. Cosine Similarity             → Compute similarity between user and courses
  5. Score Weighting               → Apply rating, popularity, difficulty weights
  6. Ranking & Filtering           → Filter, rank, and return top-N courses
"""

import pandas as pd
import numpy as np
import re
import time
from typing import List, Dict, Optional, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from loguru import logger


# ─── Role-to-Skill Mapping ────────────────────────────────────────────────────
# Maps common job roles to their required skills for skill gap analysis

ROLE_SKILLS: Dict[str, List[str]] = {
    "data scientist": [
        "python", "machine learning", "statistics", "data analysis", "SQL",
        "deep learning", "scikit-learn", "pandas", "data visualization",
        "hypothesis testing", "regression", "classification", "feature engineering"
    ],
    "machine learning engineer": [
        "python", "machine learning", "deep learning", "tensorflow", "pytorch",
        "MLOps", "docker", "kubernetes", "API development", "model deployment",
        "feature engineering", "CI/CD", "cloud computing"
    ],
    "data engineer": [
        "python", "SQL", "Apache Spark", "data pipelines", "ETL",
        "Apache Kafka", "cloud computing", "databases", "data warehousing",
        "dbt", "Airflow", "big data"
    ],
    "ai engineer": [
        "python", "deep learning", "LLMs", "transformers", "NLP",
        "computer vision", "pytorch", "tensorflow", "API development",
        "model deployment", "prompt engineering", "vector databases"
    ],
    "full stack developer": [
        "JavaScript", "React", "Node.js", "HTML", "CSS", "SQL",
        "REST APIs", "databases", "Docker", "TypeScript", "Git"
    ],
    "devops engineer": [
        "Docker", "Kubernetes", "CI/CD", "Terraform", "Linux",
        "AWS", "cloud computing", "Jenkins", "Ansible", "monitoring"
    ],
    "data analyst": [
        "SQL", "python", "data visualization", "Excel", "Tableau",
        "Power BI", "statistics", "business intelligence", "R", "reporting"
    ],
    "nlp engineer": [
        "python", "NLP", "transformers", "BERT", "Hugging Face",
        "text classification", "sentiment analysis", "pytorch", "deep learning"
    ],
    "cloud architect": [
        "AWS", "Azure", "GCP", "cloud computing", "networking",
        "security", "microservices", "Terraform", "Kubernetes", "Docker"
    ],
    "cybersecurity engineer": [
        "network security", "cryptography", "ethical hacking", "penetration testing",
        "Linux", "Python", "cloud security", "incident response", "SIEM"
    ],
    "research scientist": [
        "python", "deep learning", "statistics", "machine learning",
        "pytorch", "mathematics", "research methods", "publications", "NLP"
    ],
    "mlops engineer": [
        "MLOps", "docker", "kubernetes", "python", "CI/CD",
        "model deployment", "monitoring", "Airflow", "MLflow", "cloud computing"
    ]
}


class RecommendationEngine:
    """
    Production-grade course recommendation engine.
    
    Uses TF-IDF + Cosine Similarity with multi-factor scoring:
      - Content similarity (0.55 weight)
      - Course rating          (0.20 weight)
      - Enrollment popularity  (0.15 weight)
      - Difficulty match       (0.10 weight)
    """

    DIFFICULTY_ORDER = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
    
    # Weight factors for final recommendation score
    WEIGHTS = {
        "similarity": 0.55,
        "rating":     0.20,
        "popularity": 0.15,
        "difficulty": 0.10,
    }

    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.df: Optional[pd.DataFrame] = None
        self.tfidf_matrix = None
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.scaler = MinMaxScaler()
        self._is_ready = False

    # ─── Initialization ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load data, build features, and fit TF-IDF model."""
        logger.info("Initializing recommendation engine...")
        t0 = time.time()
        
        self._load_data()
        self._preprocess_data()
        self._build_features()
        self._fit_tfidf()
        self._compute_normalized_scores()
        
        self._is_ready = True
        elapsed = (time.time() - t0) * 1000
        logger.success(f"Engine ready — {len(self.df)} courses loaded in {elapsed:.0f}ms")

    def _load_data(self) -> None:
        """Load CSV dataset into a DataFrame."""
        logger.info(f"Loading dataset: {self.dataset_path}")
        self.df = pd.read_csv(self.dataset_path)
        logger.info(f"Loaded {len(self.df)} courses")

    def _preprocess_data(self) -> None:
        """Clean and normalize raw data."""
        df = self.df

        # Parse list columns (stored as comma-separated strings in CSV)
        df["skills_list"] = df["skills"].apply(self._parse_list_col)
        df["prerequisites_list"] = df["prerequisites"].apply(self._parse_list_col)

        # Normalize string fields
        df["title_clean"]    = df["title"].str.lower().str.strip()
        df["category_clean"] = df["category"].str.lower().str.strip()

        # Numeric cleanup
        df["rating"]         = pd.to_numeric(df["rating"], errors="coerce").fillna(4.0)
        df["enrolled"]       = pd.to_numeric(df["enrolled"], errors="coerce").fillna(0)
        df["duration_hours"] = pd.to_numeric(df["duration_hours"], errors="coerce").fillna(10)
        df["price_usd"]      = pd.to_numeric(df["price_usd"], errors="coerce").fillna(0)

        # Boolean certificate flag
        df["certificate"] = df["certificate"].astype(str).str.lower().isin(["yes", "true", "1"])

        self.df = df
        logger.info("Data preprocessed successfully")

    def _parse_list_col(self, val: Any) -> List[str]:
        """Parse comma-separated string columns into Python lists."""
        if pd.isna(val) or val == "":
            return []
        return [item.strip().lower() for item in str(val).split(",") if item.strip()]

    def _build_features(self) -> None:
        """
        Build a rich text feature string per course for TF-IDF.
        
        Feature string = title (3x weight) + skills (2x) + category + subcategory
                       + provider + description + difficulty + outcomes
        """
        def build_feature(row) -> str:
            parts = []
            # Title repeated → higher TF-IDF weight
            parts.append((row["title_clean"] + " ") * 3)
            # Skills repeated → high weight
            skills_str = " ".join(row["skills_list"])
            parts.append((skills_str + " ") * 2)
            # Categorical features
            parts.append(row.get("category", ""))
            parts.append(row.get("subcategory", ""))
            parts.append(row.get("provider", ""))
            parts.append(row.get("difficulty", ""))
            parts.append(row.get("description", ""))
            parts.append(row.get("learning_outcomes", ""))
            parts.append(" ".join(row["prerequisites_list"]))
            return " ".join(str(p) for p in parts).lower()

        self.df["feature_text"] = self.df.apply(build_feature, axis=1)
        logger.info("Feature engineering complete")

    def _fit_tfidf(self) -> None:
        """
        Fit TF-IDF vectorizer on all course feature texts.
        
        Configuration:
          - ngram_range (1,2): unigrams + bigrams for better phrase capture
          - max_features 8000: vocabulary cap for performance
          - sublinear_tf: log-scale term frequency
          - min_df 1: include rare but specific technical terms
        """
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
            min_df=1,
            max_df=0.9,
            analyzer="word",
            token_pattern=r"[a-zA-Z][a-zA-Z0-9\+\#\.]{1,}",  # tech-friendly tokenizer
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["feature_text"])
        logger.info(
            f"TF-IDF matrix: {self.tfidf_matrix.shape[0]} docs × "
            f"{self.tfidf_matrix.shape[1]} features"
        )

    def _compute_normalized_scores(self) -> None:
        """Pre-compute normalized rating and popularity scores for weighted ranking."""
        self.df["rating_norm"]     = self.scaler.fit_transform(self.df[["rating"]])[:, 0]
        enrollment_log             = np.log1p(self.df["enrolled"])  # log-scale for popularity
        self.df["popularity_norm"] = (enrollment_log - enrollment_log.min()) / \
                                     (enrollment_log.max() - enrollment_log.min() + 1e-9)

    # ─── Core Recommendation ──────────────────────────────────────────────────

    def recommend(
        self,
        current_skills: List[str],
        target_role: Optional[str] = None,
        preferred_difficulty: str = "All",
        preferred_categories: Optional[List[str]] = None,
        completed_courses: Optional[List[str]] = None,
        max_duration_hours: Optional[float] = None,
        free_only: bool = False,
        n: int = 10,
        sort_by: str = "score",
    ) -> Tuple[List[Dict], float]:
        """
        Generate top-N course recommendations.
        
        Args:
            current_skills: User's current skill list.
            target_role: Target job title for role-aware ranking.
            preferred_difficulty: Filter by difficulty level.
            preferred_categories: Filter by course categories.
            completed_courses: Exclude already-completed courses.
            max_duration_hours: Maximum course duration filter.
            free_only: Show only free courses.
            n: Number of recommendations to return.
            sort_by: Ranking metric ('score', 'rating', etc.)
        
        Returns:
            (list of course dicts with scores, processing_time_ms)
        """
        if not self._is_ready:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        t0 = time.time()
        
        # 1. Build the query vector from user's skills + target role
        query_text = self._build_query(current_skills, target_role)
        query_vec  = self.vectorizer.transform([query_text])

        # 2. Compute cosine similarity against all courses
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 3. Apply filters
        mask = self._build_filter_mask(
            preferred_difficulty, preferred_categories,
            completed_courses, max_duration_hours, free_only
        )

        # 4. Compute weighted final scores
        difficulty_scores = self._compute_difficulty_scores(current_skills, preferred_difficulty)

        # Role-category boost: courses whose category/subcategory matches the target role
        role_boost = self._compute_role_boost(target_role)

        raw_scores = (
            self.WEIGHTS["similarity"] * similarities +
            self.WEIGHTS["rating"]     * self.df["rating_norm"].values +
            self.WEIGHTS["popularity"] * self.df["popularity_norm"].values +
            self.WEIGHTS["difficulty"] * difficulty_scores +
            0.10                       * role_boost           # role alignment bonus
        )

        # 5. Apply mask (set filtered courses to -1)
        final_scores = raw_scores.copy()
        final_scores[~mask] = -1

        # 6. Pick top-N indices
        top_indices = np.argsort(final_scores)[::-1]
        top_indices = top_indices[final_scores[top_indices] > 0][:max(n * 2, 20)]

        # Normalize scores so best match → ~95, others scale relative to it
        visible_scores = final_scores[top_indices]
        score_max  = visible_scores.max() if len(visible_scores) else 1.0
        score_min  = max(visible_scores.min() if len(visible_scores) else 0.0, 0.0)
        score_range = score_max - score_min if score_max > score_min else 1.0

        def normalize(s):
            return 55.0 + 40.0 * (s - score_min) / score_range  # maps to 55–95 range

        # 7. Build result list with explanations
        results = []
        rank = 1
        user_skills_set = set(s.lower() for s in current_skills)

        for idx in top_indices:
            if rank > n:
                break
            row    = self.df.iloc[idx]
            sim    = float(similarities[idx])
            score  = float(final_scores[idx])

            if sim < 0.04:  # skip low-relevance courses
                continue

            course_skills = set(row["skills_list"])
            overlap       = list(user_skills_set & course_skills)
            reasons       = self._generate_reasons(row, sim, overlap, current_skills, target_role)

            results.append({
                **self._row_to_dict(row),
                "similarity_score":     round(sim, 4),
                "recommendation_score": round(normalize(score), 1),
                "match_reasons":        reasons,
                "skill_overlap":        overlap,
                "rank":                 rank,
            })
            rank += 1

        # 8. Sort by requested metric
        results = self._sort_results(results, sort_by)
        # Re-assign rank after sort
        for i, r in enumerate(results):
            r["rank"] = i + 1

        elapsed = (time.time() - t0) * 1000
        return results, elapsed

    def _compute_role_boost(self, target_role: Optional[str]) -> np.ndarray:
        """
        Give a boost to courses whose category/subcategory/skills
        closely match the target role. Returns values 0.0–1.0 per course.
        """
        boost = np.zeros(len(self.df))
        if not target_role:
            return boost

        role_lower = target_role.lower()

        # Map role keywords → relevant categories
        ROLE_CATEGORY_MAP = {
            "data scientist":          ["data science", "ai/ml", "statistics"],
            "machine learning":        ["ai/ml", "data science"],
            "data engineer":           ["data engineering", "big data"],
            "data analyst":            ["data science", "databases"],
            "full stack":              ["web development", "databases"],
            "frontend":                ["web development"],
            "backend":                 ["web development", "databases"],
            "devops":                  ["devops", "cloud"],
            "cloud":                   ["cloud", "devops"],
            "cybersecurity":           ["cybersecurity"],
            "nlp":                     ["ai/ml"],
            "computer vision":         ["ai/ml"],
            "mobile":                  ["mobile development"],
            "ios":                     ["mobile development"],
            "android":                 ["mobile development"],
            "game":                    ["game development"],
            "mlops":                   ["ai/ml", "devops"],
            "ai engineer":             ["ai/ml"],
            "research scientist":      ["ai/ml", "data science"],
            "blockchain":              ["blockchain"],
            "database":                ["databases"],
        }

        relevant_cats = []
        for key, cats in ROLE_CATEGORY_MAP.items():
            if key in role_lower or role_lower in key:
                relevant_cats.extend(cats)

        if not relevant_cats:
            # Fallback: partial match on category name
            for i, cat in enumerate(self.df["category"].str.lower()):
                if any(word in cat for word in role_lower.split()):
                    boost[i] = 0.5
            return boost

        for i, cat in enumerate(self.df["category"].str.lower()):
            if cat in relevant_cats:
                boost[i] = 1.0
            elif any(rc in cat for rc in relevant_cats):
                boost[i] = 0.5

        return boost

    def _build_query(self, skills: List[str], target_role: Optional[str]) -> str:
        """Build TF-IDF query string from user skills + role."""
        parts = []
        # Skills appear twice for higher importance
        skills_str = " ".join(skills)
        parts.append((skills_str + " ") * 2)

        if target_role:
            parts.append(target_role.lower())
            # Expand with role-specific skills
            role_key = target_role.lower().strip()
            for key, role_skills in ROLE_SKILLS.items():
                if key in role_key or role_key in key:
                    parts.append(" ".join(role_skills))
                    break

        return " ".join(parts)

    def _build_filter_mask(
        self,
        difficulty: str,
        categories: Optional[List[str]],
        completed: Optional[List[str]],
        max_duration: Optional[float],
        free_only: bool,
    ) -> np.ndarray:
        """Build boolean mask for filtering courses."""
        mask = np.ones(len(self.df), dtype=bool)

        # Difficulty filter
        if difficulty and difficulty != "All":
            mask &= self.df["difficulty"] == difficulty

        # Category filter
        if categories:
            cat_lower = [c.lower() for c in categories]
            mask &= self.df["category_clean"].isin(cat_lower)

        # Exclude completed
        if completed:
            mask &= ~self.df["course_id"].isin(completed)

        # Duration filter
        if max_duration:
            mask &= self.df["duration_hours"] <= max_duration

        # Free only
        if free_only:
            mask &= self.df["price_usd"] == 0

        return mask

    def _compute_difficulty_scores(self, skills: List[str], preferred: str) -> np.ndarray:
        """Score each course based on difficulty appropriateness."""
        n_skills = len(skills)
        if n_skills <= 2:
            ideal = 1   # Beginner
        elif n_skills <= 6:
            ideal = 2   # Intermediate
        else:
            ideal = 3   # Advanced

        # Override if user explicitly set preference
        if preferred and preferred != "All":
            ideal = self.DIFFICULTY_ORDER.get(preferred, ideal)

        scores = np.zeros(len(self.df))
        for i, diff in enumerate(self.df["difficulty"]):
            level = self.DIFFICULTY_ORDER.get(diff, 2)
            gap   = abs(level - ideal)
            scores[i] = 1.0 if gap == 0 else (0.6 if gap == 1 else 0.2)
        return scores

    def _generate_reasons(
        self,
        row: pd.Series,
        similarity: float,
        overlap: List[str],
        user_skills: List[str],
        target_role: Optional[str],
    ) -> List[str]:
        """Generate human-readable recommendation reasons."""
        reasons = []

        if overlap:
            top_overlap = overlap[:3]
            reasons.append(f"Matches your skills: {', '.join(top_overlap)}")

        if similarity > 0.4:
            reasons.append("Highly relevant to your profile")
        elif similarity > 0.2:
            reasons.append("Good match for your learning path")

        if target_role:
            role_key = target_role.lower()
            for key, role_skills in ROLE_SKILLS.items():
                if key in role_key or role_key in key:
                    role_overlap = set(row["skills_list"]) & set(s.lower() for s in role_skills)
                    if role_overlap:
                        reasons.append(f"Helps build skills for {target_role}")
                    break

        if row["rating"] >= 4.7:
            reasons.append(f"Top-rated course ({row['rating']}/5.0)")

        if row.get("certificate"):
            reasons.append("Includes certification")

        if row["enrolled"] > 500000:
            reasons.append("Popular course (500K+ enrolled)")

        return reasons[:4]  # Cap at 4 reasons

    def _sort_results(self, results: List[Dict], sort_by: str) -> List[Dict]:
        """Sort results by the requested metric."""
        key_map = {
            "score":    lambda x: x["recommendation_score"],
            "rating":   lambda x: x["rating"],
            "enrolled": lambda x: x["enrolled"],
            "duration": lambda x: x["duration_hours"],
        }
        key_fn = key_map.get(sort_by, key_map["score"])
        return sorted(results, key=key_fn, reverse=True)

    def _row_to_dict(self, row: pd.Series) -> Dict:
        """Convert DataFrame row to API-friendly dict."""
        return {
            "course_id":        row["course_id"],
            "title":            row["title"],
            "platform":         row["platform"],
            "provider":         row["provider"],
            "category":         row["category"],
            "subcategory":      row["subcategory"],
            "skills":           row["skills_list"],
            "difficulty":       row["difficulty"],
            "duration_hours":   float(row["duration_hours"]),
            "rating":           float(row["rating"]),
            "enrolled":         int(row["enrolled"]),
            "price_usd":        float(row["price_usd"]),
            "certificate":      bool(row["certificate"]),
            "description":      row["description"],
            "url_slug":         row["url_slug"],
            "prerequisites":    row["prerequisites_list"],
            "learning_outcomes": row["learning_outcomes"],
        }

    # ─── Skill Gap Analysis ───────────────────────────────────────────────────

    def analyze_skill_gap(
        self, current_skills: List[str], target_role: str
    ) -> Dict:
        """Compute the skill gap between user's current skills and a target role."""
        user_skills = set(s.lower() for s in current_skills)
        role_key    = target_role.lower().strip()

        # Find best-matching role in our mapping
        required_skills = []
        for key, skills in ROLE_SKILLS.items():
            if key in role_key or role_key in key:
                required_skills = [s.lower() for s in skills]
                break

        if not required_skills:
            # Fallback: infer from matching courses
            role_courses = self._find_role_courses(target_role)
            for _, row in role_courses.iterrows():
                required_skills.extend(row["skills_list"])
            required_skills = list(set(required_skills))[:15]

        required_set    = set(required_skills)
        missing_skills  = list(required_set - user_skills)
        overlap_skills  = list(required_set & user_skills)
        gap_pct         = (len(missing_skills) / len(required_set) * 100) if required_set else 0

        # Prioritize missing skills by their frequency in top courses
        priority = self._prioritize_skills(missing_skills, target_role)

        # Get courses for the missing skills
        recs, _ = self.recommend(
            current_skills=list(user_skills | set(priority[:5])),
            target_role=target_role,
            n=8
        )

        return {
            "target_role":        target_role,
            "current_skills":     list(user_skills),
            "required_skills":    required_skills,
            "missing_skills":     missing_skills,
            "proficiency_skills": overlap_skills,
            "gap_percentage":     round(gap_pct, 1),
            "priority_skills":    priority[:6],
            "recommended_courses": recs,
        }

    def _find_role_courses(self, role: str, n: int = 20) -> pd.DataFrame:
        """Find courses most relevant to a job role."""
        role_lower = role.lower()
        cat_mask   = self.df["category_clean"].str.contains(role_lower, na=False)
        sub_mask   = self.df["subcategory"].str.lower().str.contains(role_lower, na=False)
        return self.df[cat_mask | sub_mask].head(n)

    def _prioritize_skills(self, missing: List[str], role: str) -> List[str]:
        """Rank missing skills by importance (freq in relevant courses)."""
        if not missing:
            return []
        role_courses = self._find_role_courses(role, 30)
        freq = {skill: 0 for skill in missing}
        for _, row in role_courses.iterrows():
            for skill in row["skills_list"]:
                if skill in freq:
                    freq[skill] += 1
        return sorted(missing, key=lambda s: freq.get(s, 0), reverse=True)

    # ─── Learning Roadmap ─────────────────────────────────────────────────────

    def generate_roadmap(
        self, current_skills: List[str], target_role: str, timeframe_months: int = 6
    ) -> Dict:
        """Generate a phased learning roadmap toward a target role."""
        gap  = self.analyze_skill_gap(current_skills, target_role)
        recs, _ = self.recommend(
            current_skills=current_skills,
            target_role=target_role,
            n=18
        )

        # Split recommendations across phases
        phases_count = min(3, timeframe_months // 2 + 1)
        phase_size   = max(1, len(recs) // phases_count)
        weeks_per    = (timeframe_months * 4) // phases_count

        phase_labels = [
            ("Foundation",   "Build core foundational skills"),
            ("Core Skills",  "Develop key domain expertise"),
            ("Advanced",     "Specialize and apply advanced techniques"),
            ("Mastery",      "Polish and project-based learning"),
        ]

        phases = []
        for i in range(phases_count):
            start = i * phase_size
            chunk = recs[start: start + phase_size]
            label, desc = phase_labels[min(i, len(phase_labels) - 1)]

            phase_skills = []
            for c in chunk:
                phase_skills.extend(c.get("skills", [])[:3])

            phases.append({
                "phase_number":    i + 1,
                "title":           f"Phase {i+1}: {label}",
                "duration_weeks":  weeks_per,
                "description":     desc,
                "skills_to_learn": list(set(phase_skills))[:6],
                "courses":         chunk,
                "milestone":       f"Complete {len(chunk)} course(s) and practice {phase_skills[0] if phase_skills else 'core skills'}",
            })

        total_hours = sum(c["duration_hours"] for r in phases for c in r["courses"])

        return {
            "target_role":       target_role,
            "total_duration_months": timeframe_months,
            "overview": (
                f"A structured {timeframe_months}-month path to becoming a {target_role}. "
                f"You have {len(gap['proficiency_skills'])} relevant skills already. "
                f"Focus on {len(gap['missing_skills'])} missing skills across {phases_count} phases."
            ),
            "phases":          phases,
            "total_courses":   sum(len(p["courses"]) for p in phases),
            "estimated_hours": round(total_hours, 1),
        }

    # ─── Dataset Statistics ───────────────────────────────────────────────────

    def get_statistics(self) -> Dict:
        """Return descriptive statistics about the loaded dataset."""
        if not self._is_ready:
            return {}

        # Count skill occurrences across all courses
        all_skills: Dict[str, int] = {}
        for skills in self.df["skills_list"]:
            for s in skills:
                all_skills[s] = all_skills.get(s, 0) + 1

        top_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:20]

        return {
            "total_courses":            len(self.df),
            "platforms":                self.df["platform"].value_counts().to_dict(),
            "categories":               self.df["category"].value_counts().to_dict(),
            "difficulty_distribution":  self.df["difficulty"].value_counts().to_dict(),
            "average_rating":           round(float(self.df["rating"].mean()), 2),
            "skill_count":              len(all_skills),
            "top_skills":               [{"skill": s, "count": c} for s, c in top_skills],
        }

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def course_count(self) -> int:
        return len(self.df) if self.df is not None else 0

    def get_all_skills(self) -> List[str]:
        """Return all unique skills across all courses."""
        all_skills = set()
        for skills in self.df["skills_list"]:
            all_skills.update(skills)
        return sorted(all_skills)

    def get_all_categories(self) -> List[str]:
        return sorted(self.df["category"].unique().tolist())

    def get_all_roles(self) -> List[str]:
        return [r.title() for r in ROLE_SKILLS.keys()]
