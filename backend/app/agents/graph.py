"""
LangGraph StateGraph definition.

Flow:
  START → [resume_extractor, jd_extractor] (parallel fan-out via Send)
       → matcher → suggester → HITL interrupt
  resume: POST /api/confirm injects user_feedback → rewriter → END
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.nodes import (
    jd_extractor,
    matcher,
    resume_extractor,
    rewriter,
    suggester,
)
from app.agents.state import AgentState


def _route_start(state: AgentState) -> list[Send]:
    return [
        Send("resume_extractor", state),
        Send("jd_extractor", state),
    ]


def _hitl_node(state: AgentState) -> dict:
    """Pause here; returns suggestions to caller via interrupt()."""
    interrupt({"suggestions": [s.model_dump() for s in state.get("suggestions", [])]})
    return {}


def build_graph() -> tuple:
    """Return (compiled_graph, checkpointer)."""
    checkpointer = MemorySaver()

    builder = StateGraph(AgentState)
    builder.add_node("resume_extractor", resume_extractor)
    builder.add_node("jd_extractor", jd_extractor)
    builder.add_node("matcher", matcher)
    builder.add_node("suggester", suggester)
    builder.add_node("hitl", _hitl_node)
    builder.add_node("rewriter", rewriter)

    # parallel fan-out from START
    builder.add_conditional_edges(START, _route_start)

    builder.add_edge("resume_extractor", "matcher")
    builder.add_edge("jd_extractor", "matcher")
    builder.add_edge("matcher", "suggester")
    builder.add_edge("suggester", "hitl")
    builder.add_edge("hitl", "rewriter")
    builder.add_edge("rewriter", END)

    graph = builder.compile(checkpointer=checkpointer, interrupt_before=["rewriter"])
    return graph, checkpointer


# module-level singleton
graph, checkpointer = build_graph()
