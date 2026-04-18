import re

from langchain_core.tools import tool


@tool
def extract_keywords(text: str) -> list[str]:
    """Extract tech skills, tools, languages, and role keywords from text."""
    # simple regex pre-filter; LLM node uses this as fallback/supplement
    patterns = [
        r"\b(Python|Java|Go|Rust|TypeScript|JavaScript|C\+\+|C#|Ruby|Swift|Kotlin)\b",
        r"\b(FastAPI|Django|Flask|Spring|React|Vue|Angular|Next\.?js|Node\.?js)\b",
        r"\b(PostgreSQL|MySQL|Redis|MongoDB|Elasticsearch|Kafka|RabbitMQ)\b",
        r"\b(Docker|Kubernetes|Terraform|AWS|GCP|Azure|CI/CD|GitHub Actions)\b",
        r"\b(LangChain|LangGraph|PyTorch|TensorFlow|HuggingFace|OpenAI|DeepSeek)\b",
        r"\b(REST|GraphQL|gRPC|WebSocket|MQTT|OAuth|JWT)\b",
    ]
    keywords: set[str] = set()
    for pat in patterns:
        keywords.update(re.findall(pat, text, re.IGNORECASE))
    return list(keywords)


@tool
def score_skill_match(resume_skills: list[str], jd_skills: list[str]) -> dict:
    """Calculate intersection/gap ratio between resume and JD skills."""
    rs = {s.lower() for s in resume_skills}
    js = {s.lower() for s in jd_skills}
    matched = rs & js
    missing = js - rs
    score = int(len(matched) / max(len(js), 1) * 100)
    return {
        "score": score,
        "matched": list(matched),
        "missing": list(missing),
    }


@tool
def format_report(highlights: list[str], gaps: list[str], score: int) -> dict:
    """Format matcher output into a structured MatchReport dict."""
    return {"score": score, "highlights": highlights, "gaps": gaps}
