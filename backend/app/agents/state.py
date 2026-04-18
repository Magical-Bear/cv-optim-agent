from typing import Annotated, TypedDict

import operator
from pydantic import BaseModel


class MatchReport(BaseModel):
    score: int
    highlights: list[str]
    gaps: list[str]


class Suggestion(BaseModel):
    id: str
    priority: str  # high | mid | low
    original_text: str
    suggested_text: str


class UserFeedback(BaseModel):
    selected_suggestions: list[str] = []
    edited_suggestions: list[dict] = []
    extra_note: str = ""


class AgentState(TypedDict):
    resume_text: str
    jd_text: str
    # parallel fan-out merges via list concatenation reducer
    resume_keywords: Annotated[list[str], operator.add]
    jd_keywords: Annotated[list[str], operator.add]
    match_report: MatchReport | None
    suggestions: list[Suggestion]
    user_feedback: UserFeedback | None
    optimized_resume: str
