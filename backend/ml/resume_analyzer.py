"""
Resume Analyzer Module
Extracts skills from resume text using NLP pattern matching and keyword detection.
"""

import re
from typing import List, Dict, Tuple
from loguru import logger


# Comprehensive skill taxonomy organized by domain
SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Programming Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "r", "go",
        "rust", "scala", "kotlin", "swift", "ruby", "php", "matlab", "julia",
        "bash", "shell", "perl", "dart", "elixir"
    ],
    "Machine Learning & AI": [
        "machine learning", "deep learning", "neural networks", "reinforcement learning",
        "transfer learning", "ensemble methods", "feature engineering", "model deployment",
        "scikit-learn", "xgboost", "lightgbm", "catboost", "mlops", "automl",
        "federated learning", "causal inference", "recommender systems"
    ],
    "Deep Learning Frameworks": [
        "tensorflow", "pytorch", "keras", "jax", "fast.ai", "mxnet", "caffe",
        "hugging face", "transformers", "diffusers", "onnx"
    ],
    "Natural Language Processing": [
        "nlp", "bert", "gpt", "llm", "large language models", "transformers",
        "text classification", "sentiment analysis", "ner", "named entity recognition",
        "text generation", "question answering", "langchain", "llamaindex",
        "rag", "retrieval augmented generation", "prompt engineering", "fine-tuning",
        "tokenization", "word embeddings", "word2vec", "spacy", "nltk"
    ],
    "Computer Vision": [
        "computer vision", "cnn", "object detection", "image classification",
        "image segmentation", "yolo", "opencv", "pillow", "image processing",
        "gan", "stable diffusion", "face recognition", "pose estimation"
    ],
    "Data Science": [
        "data analysis", "data visualization", "exploratory data analysis", "eda",
        "statistical analysis", "hypothesis testing", "a/b testing", "pandas",
        "numpy", "matplotlib", "seaborn", "plotly", "tableau", "power bi",
        "data wrangling", "data cleaning", "feature selection"
    ],
    "Databases & SQL": [
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "oracle", "sqlite", "nosql", "graph database",
        "neo4j", "vector database", "pinecone", "weaviate", "chroma"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "github actions", "ci/cd", "microservices",
        "serverless", "lambda", "cloud formation", "helm", "istio"
    ],
    "Web Development": [
        "react", "angular", "vue", "node.js", "express", "django", "flask",
        "fastapi", "spring boot", "html", "css", "rest api", "graphql",
        "next.js", "nuxt", "webpack", "tailwind", "bootstrap", "typescript"
    ],
    "Data Engineering": [
        "apache spark", "pyspark", "hadoop", "kafka", "airflow", "dbt",
        "data pipelines", "etl", "data warehouse", "data lake", "bigquery",
        "snowflake", "databricks", "flink", "nifi", "luigi", "prefect"
    ],
    "Statistics & Mathematics": [
        "statistics", "probability", "linear algebra", "calculus", "regression",
        "classification", "clustering", "dimensionality reduction", "pca",
        "bayesian", "time series", "forecasting", "optimization", "simulation"
    ],
    "Soft Skills": [
        "project management", "agile", "scrum", "communication", "teamwork",
        "leadership", "problem solving", "critical thinking", "research"
    ],
}


def extract_skills_from_resume(resume_text: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Extract skills from resume text using pattern matching.
    
    Returns:
        (all_skills, categorized_skills_dict)
    """
    text_lower = resume_text.lower()
    # Normalize whitespace
    text_normalized = re.sub(r'\s+', ' ', text_lower)

    found_skills: List[str] = []
    categorized: Dict[str, List[str]] = {}

    for category, skills in SKILL_TAXONOMY.items():
        cat_found = []
        for skill in skills:
            # Use word boundary matching for accuracy
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_normalized):
                found_skills.append(skill)
                cat_found.append(skill)
        if cat_found:
            categorized[category] = cat_found

    # Deduplicate while preserving order
    seen = set()
    unique_skills = []
    for s in found_skills:
        if s not in seen:
            seen.add(s)
            unique_skills.append(s)

    logger.info(f"Extracted {len(unique_skills)} skills from resume")
    return unique_skills, categorized


def calculate_skill_strength(skills: List[str], categorized: Dict[str, List[str]]) -> float:
    """
    Calculate a skill strength score (0-100) based on breadth and depth.
    """
    if not skills:
        return 0.0

    breadth_score = min(len(skills) / 25 * 50, 50)          # Up to 50 pts for breadth
    depth_score   = min(len(categorized) / 5 * 30, 30)       # Up to 30 pts for depth across domains
    # Bonus for having key technical skills
    key_skills = {"python", "machine learning", "sql", "deep learning", "aws", "docker"}
    bonus = min(len(set(skills) & key_skills) * 5, 20)        # Up to 20 pts bonus

    return round(min(breadth_score + depth_score + bonus, 100), 1)


def suggest_roles(skills: List[str]) -> List[str]:
    """Suggest job roles based on extracted skills."""
    from backend.ml.engine import ROLE_SKILLS
    
    user_set = set(s.lower() for s in skills)
    role_scores: Dict[str, float] = {}

    for role, required in ROLE_SKILLS.items():
        req_set = set(s.lower() for s in required)
        overlap = user_set & req_set
        score   = len(overlap) / len(req_set) if req_set else 0
        if score > 0.2:  # at least 20% skill match
            role_scores[role.title()] = score

    return sorted(role_scores, key=lambda r: role_scores[r], reverse=True)[:5]
