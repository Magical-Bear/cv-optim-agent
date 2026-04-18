"""
LangGraph StateGraph definition.

Flow:
  START → [resume_extractor, jd_extractor] (parallel fan-out via Send)
       → matcher → suggester → END

  /api/analyze runs this graph and returns suggestions.
  /api/confirm calls rewriter node directly — no HITL interrupt needed.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

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


def build_graph() -> tuple:
    """Return (compiled_graph, checkpointer)."""
    checkpointer = MemorySaver()

    builder = StateGraph(AgentState)
    builder.add_node("resume_extractor", resume_extractor)
    builder.add_node("jd_extractor", jd_extractor)
    builder.add_node("matcher", matcher)
    builder.add_node("suggester", suggester)
    builder.add_node("rewriter", rewriter)

    # parallel fan-out from START
    builder.add_conditional_edges(START, _route_start)

    builder.add_edge("resume_extractor", "matcher")
    builder.add_edge("jd_extractor", "matcher")
    builder.add_edge("matcher", "suggester")
    builder.add_edge("suggester", END)
    # rewriter is invoked separately via /api/confirm, not chained here

    graph = builder.compile(checkpointer=checkpointer)
    return graph, checkpointer


# module-level singleton
graph, checkpointer = build_graph()
