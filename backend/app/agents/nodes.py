"""
5 LangGraph node functions.
Each takes AgentState, returns partial state dict.
"""
import json

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState, MatchReport, Suggestion
from app.agents.tools import extract_keywords, format_report, score_skill_match
from app.config import settings


def _llm(tools: list | None = None) -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )
    if tools:
        return llm.bind_tools(tools)
    return llm


# ── Node 1: resume_extractor ────────────────────────────────────────────────

def resume_extractor(state: AgentState) -> dict:
    llm = _llm(tools=[extract_keywords])
    prompt = (
        "Extract all technical skills, tools, languages, frameworks, and role keywords "
        "from the following resume. Be exhaustive. Return a JSON array of strings.\n\n"
        f"RESUME:\n{state['resume_text']}\n\n"
        "Respond ONLY with a JSON array, e.g. [\"Python\", \"FastAPI\", ...]"
    )
    response = llm.invoke(prompt)
    # try tool call result first, fallback to text parse
    try:
        if hasattr(response, "tool_calls") and response.tool_calls:
            keywords = response.tool_calls[0]["args"].get("text", "")
            parsed = extract_keywords.invoke({"text": state["resume_text"]})
        else:
            content = response.content.strip()
            start = content.find("[")
            end = content.rfind("]") + 1
            parsed = json.loads(content[start:end]) if start != -1 else []
    except Exception:
        parsed = extract_keywords.invoke({"text": state["resume_text"]})

    return {"resume_keywords": list(parsed) if parsed else []}


# ── Node 2: jd_extractor ───────────────────────────────────────────────────

def jd_extractor(state: AgentState) -> dict:
    llm = _llm(tools=[extract_keywords])
    prompt = (
        "Extract required and preferred skills/keywords from this job description. "
        "Return a JSON array of strings.\n\n"
        f"JD:\n{state['jd_text']}\n\n"
        "Respond ONLY with a JSON array."
    )
    response = llm.invoke(prompt)
    try:
        if hasattr(response, "tool_calls") and response.tool_calls:
            parsed = extract_keywords.invoke({"text": state["jd_text"]})
        else:
            content = response.content.strip()
            start = content.find("[")
            end = content.rfind("]") + 1
            parsed = json.loads(content[start:end]) if start != -1 else []
    except Exception:
        parsed = extract_keywords.invoke({"text": state["jd_text"]})

    return {"jd_keywords": list(parsed) if parsed else []}


# ── Node 3: matcher ────────────────────────────────────────────────────────

def matcher(state: AgentState) -> dict:
    resume_kw = state.get("resume_keywords", [])
    jd_kw = state.get("jd_keywords", [])

    # quick score via tool
    score_data = score_skill_match.invoke(
        {"resume_skills": resume_kw, "jd_skills": jd_kw}
    )

    llm = _llm()
    prompt = (
        "Compare resume keywords vs JD keywords and write a match analysis.\n\n"
        f"Resume keywords: {resume_kw}\n"
        f"JD keywords: {jd_kw}\n"
        f"Pre-calculated score: {score_data['score']}, matched: {score_data['matched']}, "
        f"missing: {score_data['missing']}\n\n"
        "Output JSON with keys: score (int 0-100), highlights (list[str]), gaps (list[str]).\n"
        "highlights = skills resume has that match JD (with evidence phrase).\n"
        "gaps = required JD skills missing from resume.\n"
        "Respond ONLY with JSON."
    )
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        data = json.loads(content[start:end])
        report = MatchReport(
            score=data.get("score", score_data["score"]),
            highlights=data.get("highlights", score_data["matched"]),
            gaps=data.get("gaps", score_data["missing"]),
        )
    except Exception:
        report = MatchReport(
            score=score_data["score"],
            highlights=score_data["matched"],
            gaps=score_data["missing"],
        )

    return {"match_report": report}


# ── Node 4: suggester ──────────────────────────────────────────────────────

def suggester(state: AgentState) -> dict:
    report = state.get("match_report")
    llm = _llm()
    prompt = (
        "Generate 5-8 specific, actionable improvement suggestions to optimize this resume for the JD.\n\n"
        f"RESUME:\n{state['resume_text']}\n\n"
        f"JD:\n{state['jd_text']}\n\n"
        f"Match gaps: {report.gaps if report else []}\n\n"
        "Each suggestion must have:\n"
        "  id: string like 's1', 's2', ...\n"
        "  priority: 'high' | 'mid' | 'low'\n"
        "  original_text: exact current resume phrase to change (or '' if adding new)\n"
        "  suggested_text: concrete rewrite\n\n"
        "Output ONLY a JSON array of suggestion objects."
    )
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        raw = json.loads(content[start:end])
        suggestions = [Suggestion(**s) for s in raw]
    except Exception:
        suggestions = []

    return {"suggestions": suggestions}


# ── Node 5: rewriter ───────────────────────────────────────────────────────

def rewriter(state: AgentState) -> dict:
    feedback = state.get("user_feedback")
    suggestions = state.get("suggestions", [])

    selected_ids = set(feedback.selected_suggestions) if feedback else set()
    edited_map = (
        {e["id"]: e["suggested_text"] for e in feedback.edited_suggestions}
        if feedback
        else {}
    )
    # merge edited into selected
    selected_ids.update(edited_map.keys())

    applied: list[dict] = []
    for s in suggestions:
        if s.id in edited_map:
            applied.append({"original": s.original_text, "replacement": edited_map[s.id]})
        elif s.id in selected_ids:
            applied.append({"original": s.original_text, "replacement": s.suggested_text})

    extra = feedback.extra_note if feedback else ""

    llm = _llm()
    prompt = (
        "Rewrite the resume applying ONLY the user-selected suggestions listed below. "
        "Keep all other content unchanged. Output clean Markdown.\n\n"
        f"ORIGINAL RESUME:\n{state['resume_text']}\n\n"
        f"CHANGES TO APPLY:\n{json.dumps(applied, ensure_ascii=False, indent=2)}\n\n"
        + (f"EXTRA INSTRUCTION: {extra}\n\n" if extra else "")
        + "Output ONLY the optimized resume in Markdown format."
    )
    response = llm.invoke(prompt)
    return {"optimized_resume": response.content.strip()}
