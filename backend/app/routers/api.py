import asyncio
import uuid
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from langgraph.types import Command
from pydantic import BaseModel

from app.agents.graph import graph
from app.agents.state import UserFeedback
from app.config import settings
from app.session import create_session, get_session
from app.utils.exporter import export_md, export_pdf
from app.utils.parser import parse_file

router = APIRouter()


# ── /api/upload ────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(400, "File too large")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx"):
        raise HTTPException(400, "Unsupported file type. Upload .pdf or .docx")

    try:
        text = await asyncio.to_thread(parse_file, data, ext)
    except Exception as e:
        raise HTTPException(500, f"Parse failure: {e}. Try pasting text instead.")

    sid = create_session()
    return {"session_id": sid, "text": text}


# ── /api/analyze ───────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    session_id: str
    resume_text: str
    jd_text: str


@router.post("/analyze")
async def analyze(body: AnalyzeRequest):
    if not body.resume_text.strip():
        raise HTTPException(400, "resume_text is empty")
    if not body.jd_text.strip():
        raise HTTPException(400, "jd_text is empty")

    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(404, "session_id not found or expired")

    thread_id = body.session_id
    config = {"configurable": {"thread_id": thread_id}}
    session.graph_config = config

    initial_state = {
        "resume_text": body.resume_text,
        "jd_text": body.jd_text,
        "resume_keywords": [],
        "jd_keywords": [],
        "match_report": None,
        "suggestions": [],
        "user_feedback": None,
        "optimized_resume": "",
    }

    try:
        # runs until interrupt_before=["rewriter"]
        result = await asyncio.to_thread(graph.invoke, initial_state, config)
    except Exception as e:
        raise HTTPException(500, f"LangGraph failure: {e}")

    # grab state after interrupt
    snapshot = graph.get_state(config)
    state_vals = snapshot.values

    match_report = state_vals.get("match_report")
    suggestions = state_vals.get("suggestions", [])

    session.match_report = match_report
    session.suggestions = suggestions

    return {
        "match_report": match_report.model_dump() if match_report else {},
        "suggestions": [s.model_dump() for s in suggestions],
    }


# ── /api/confirm ───────────────────────────────────────────────────────────

class EditedSuggestion(BaseModel):
    id: str
    suggested_text: str


class ConfirmRequest(BaseModel):
    session_id: str
    selected_suggestions: list[str] = []
    edited_suggestions: list[EditedSuggestion] = []
    extra_note: str = ""


@router.post("/confirm")
async def confirm(body: ConfirmRequest):
    if not body.selected_suggestions and not body.edited_suggestions:
        raise HTTPException(400, "No suggestions selected")

    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(404, "session_id not found or expired")

    config = session.graph_config
    feedback = UserFeedback(
        selected_suggestions=body.selected_suggestions,
        edited_suggestions=[e.model_dump() for e in body.edited_suggestions],
        extra_note=body.extra_note,
    )

    try:
        result = await asyncio.to_thread(
            graph.invoke,
            Command(resume={"user_feedback": feedback}),
            config,
        )
    except Exception as e:
        raise HTTPException(500, f"LangGraph failure: {e}")

    optimized = result.get("optimized_resume", "")
    session.optimized_resume = optimized
    return {"optimized_resume": optimized}


# ── /api/export/{session_id} ───────────────────────────────────────────────

@router.get("/export/{session_id}")
async def export(session_id: str, format: str = Query("md", pattern="^(md|pdf)$")):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session_id not found or expired")
    if not session.optimized_resume:
        raise HTTPException(404, "No optimized resume found. Run /api/confirm first.")

    if format == "md":
        content = export_md(session.optimized_resume)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="resume_optimized.md"'},
        )
    else:
        try:
            pdf_bytes = await asyncio.to_thread(export_pdf, session.optimized_resume)
        except Exception as e:
            raise HTTPException(500, f"PDF generation failure: {e}")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="resume_optimized.pdf"'},
        )
