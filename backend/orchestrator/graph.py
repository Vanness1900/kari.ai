"""LangGraph StateGraph for the classroom simulation (CLAUDE.md sketch).

What is LangGraph?
---------------------------------
- You define a **workflow** as a **directed graph**: circles = *nodes*, arrows = *edges*.
- A single shared dict-like object, **`ClassroomState`** (see ``state.py``), is passed through
  the graph. Each **node** is a Python function that receives the current state and returns
  **only the keys it wants to change** (a *partial update*). LangGraph merges that into state.
- **`START`** / **`END`** are special markers for where the run begins and finishes.
- **`add_conditional_edges`** means: “leave this node by calling a small **router** function
  that inspects state and returns a **string label**; follow the edge with that label.”

Execution order in THIS file (happy path):
------------------------------------------
START → orchestrator → timekeeper → *(timestep 2: student_questions →)* teacher → student_swarm
→ peer_contagion → stats → *(router decides)* → bump_timestep OR advance_module OR assessor_phase → insight → END

Timesteps 1–5 per module: deliver → qna → exercise → assess → update. Confusion relief is **QNA
(timestep 2)**, not a separate re-teach loop. The router advances timestep or module, or runs
insight after the last module’s timestep 5.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from orchestrator.nodes import (
    advance_module_node,
    assessor_node,
    bump_timestep_node,
    insight_node,
    orchestrator_node,
    peer_contagion_node,
    stats_node,
    student_questions_node,
    student_swarm_node,
    teacher_node,
    timekeeper_node,
)
from orchestrator.state import ClassroomState, CurriculumConfig, StudentProfileDict

# Router labels after the per-timestep stats node.
LoopRoute = Literal["next_timestep", "advance_module", "run_assessor_phase"]

# After timekeeper: timestep 2 collects questions first, then the teacher answers (QNA face).
TeachingRoute = Literal["collect_questions", "teacher_only"]


def route_after_timekeeper(state: ClassroomState) -> TeachingRoute:
    """Timestep 2 — QNA: students ask, then teacher answers (same round as ``student_swarm``)."""
    if state["current_timestep"] == 2:
        return "collect_questions"
    return "teacher_only"


def route_after_stats(state: ClassroomState) -> LoopRoute:
    """
    Router: after one timestep's teaching + student updates + stats, where do we go next?

    1) **next_timestep** — still within timesteps 1..5 for this module → bump and loop.

    2) **run_assessor_phase** — finished timestep 5 on the *last* module → assess students.

    3) **advance_module** — finished timestep 5 with more modules → next module, timestep 1.
    """
    # Still animating the five internal phases of the *current* module
    if state["current_timestep"] < 5:
        return "next_timestep"

    modules = state["curriculum"].get("modules") or []
    # On the last module index, go run post-course assessor phase next.
    if state["current_module"] >= len(modules) - 1:
        return "run_assessor_phase"

    # Middle of course: roll forward to the next module
    return "advance_module"


def build_graph():
    """
    Assemble nodes and edges into a runnable graph, then **compile** it to an executable object.

    `StateGraph(ClassroomState)` tells LangGraph the shape of your state (for type hints and
    reducer fields like list appends — see ``state.py`` for ``Annotated[..., operator.add]``).
    """
    g = StateGraph(ClassroomState)

    # --- Register node names → callables from ``nodes.py`` (each wraps an ``agents/*.py`` stub) ---
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("timekeeper", timekeeper_node)
    g.add_node("student_questions", student_questions_node)
    g.add_node("teacher", teacher_node)
    g.add_node("student_swarm", student_swarm_node)
    g.add_node("peer_contagion", peer_contagion_node)
    g.add_node("stats", stats_node)
    g.add_node("assessor_phase", assessor_node)
    g.add_node("bump_timestep", bump_timestep_node)
    g.add_node("advance_module", advance_module_node)
    g.add_node("insight", insight_node)

    # --- Linear “teaching pipeline” for one pass through deliver → students → assess ---
    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "timekeeper")
    g.add_conditional_edges(
        "timekeeper",
        route_after_timekeeper,
        {
            "collect_questions": "student_questions",
            "teacher_only": "teacher",
        },
    )
    g.add_edge("student_questions", "teacher")
    g.add_edge("teacher", "student_swarm")
    g.add_edge("student_swarm", "peer_contagion")
    g.add_edge("peer_contagion", "stats")

    # Router: after per-timestep stats, advance timestep/module or enter assessor phase.
    g.add_conditional_edges(
        "stats",
        route_after_stats,
        {
            "next_timestep": "bump_timestep",
            "advance_module": "advance_module",
            "run_assessor_phase": "assessor_phase",
        },
    )

    # After bumping the clock or changing module, revisit orchestrator so every “round”
    # can start from the same hub (matches CLAUDE.md diagram style).
    g.add_edge("bump_timestep", "orchestrator")
    g.add_edge("advance_module", "orchestrator")

    # Assessor phase: assess all students (optionally parallel) then run insight.
    g.add_edge("assessor_phase", "insight")
    g.add_edge("insight", END)  # terminal: no outgoing edges

    return g.compile()


# Lazy singleton: building the graph once per process avoids re-parsing the workflow on every HTTP call.
_compiled_graph = None


def get_graph():
    """Return the compiled graph, building it the first time only."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def blank_classroom_state(
    session_id: str,
    *,
    curriculum: CurriculumConfig | None = None,
    students: list[StudentProfileDict] | None = None,
) -> ClassroomState:
    """
    Factory for a minimal valid initial state so ``graph.invoke(...)`` has every required key.

    TypedDict acts like a plain dict at runtime; LangGraph will merge node outputs into this.
    """
    if curriculum is None:
        curriculum = {
            "title": "Stub curriculum",
            "modules": [
                {"id": "m0", "title": "Introduction", "content": "", "blooms_level": 2},
                {"id": "m1", "title": "Practice", "content": "", "blooms_level": 3},
            ],
        }
    if students is None:
        students = [
            {
                "id": "stu_1",
                "name": "Stub Student",
                "learning_style": "visual",
                "attention_span_mins": 15,
                "social_anxiety": 0.3,
                "motivation": 0.8,
                "peer_influence": 0.4,
                "knowledge_state": {"intro": 0.2},
                "misconceptions": [],
                "confusion_level": 0.25,
                "attention_remaining": 0.9,
                "cumulative_fatigue": 0.0,
            }
        ]
    return ClassroomState(
        session_id=session_id,
        curriculum=curriculum,
        students=students,
        current_module=0,
        current_timestep=1,
        timestep_logs=[],
        module_results=[],
        student_assessments=None,
        assessor_index=0,
        simulation_complete=False,
        insight_report=None,
        current_lesson=None,
        module_delivery_snapshot=None,
        qna_student_questions=[],
    )


def run_simulation(initial: ClassroomState) -> ClassroomState:
    """
    Run the whole graph once from ``initial`` until it hits ``END``.

    ``recursion_limit`` is LangGraph’s safety budget: one “step” ≈ visiting one node.
    If it is too low, you get ``GraphRecursionError`` even if your logic is fine — so we
    scale a bit with module count.
    """
    graph = get_graph()
    n_mod = len(initial["curriculum"].get("modules") or []) or 1
    recursion_limit = max(120, n_mod * 40)
    final = graph.invoke(initial, config={"recursion_limit": recursion_limit})
    return final
