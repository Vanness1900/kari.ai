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
START → orchestrator → timekeeper → teacher → student_swarm → peer_contagion → assessor
→ *(router decides)* → bump_timestep OR advance_module OR reteach OR insight → END

The router implements: re-teach loops, advancing timestep 1→5 within a module, advancing
to the next module, and finally running the insight agent once on the last module.
"""

from __future__ import annotations

from statistics import mean
from typing import Literal

from langgraph.graph import END, START, StateGraph

from orchestrator.nodes import (
    advance_module_node,
    assessor_node,
    bump_timestep_node,
    insight_node,
    orchestrator_node,
    peer_contagion_node,
    reteach_prep_node,
    student_swarm_node,
    teacher_node,
    timekeeper_node,
)
from orchestrator.state import ClassroomState, CurriculumConfig, StudentProfileDict

# Every return from ``route_after_assessor`` must match a key in the dict passed to
# ``add_conditional_edges`` below. Think of these as “exit labels” from the assessor node.
GraphRoute = Literal["reteach", "next_timestep", "advance_module", "run_insight"]


def _avg_confusion(state: ClassroomState) -> float:
    """Helper: average ``confusion_level`` across all students (used for re-teach routing)."""
    levels = [float(s.get("confusion_level", 0.0)) for s in state["students"]]
    return mean(levels) if levels else 0.0


def route_after_assessor(state: ClassroomState) -> GraphRoute:
    """
    Router: after grading, where do we go next?

    Checked **top to bottom** — first match wins (like an if/elif chain):

    1) **reteach** — class is still too confused *and* we have not hit the re-teach cap (2).
       Send flow to ``reteach_prep`` → teacher again (same timestep; no clock bump).

    2) **next_timestep** — still inside the same module “day” (timesteps 1..5 in CLAUDE.md).
       We bump ``current_timestep`` and loop back through orchestrator → delivery chain.

    3) **run_insight** — we finished timestep 5 on the *last* module. One final node
       writes ``insight_report`` and sets ``simulation_complete``.

    4) **advance_module** — we finished timestep 5 but more modules remain: move to the next
       module, reset timestep to 1, clear re-teach counter, then loop back via orchestrator.
    """
    # Re-teach gate (confusion + cap from CLAUDE.md)
    if _avg_confusion(state) > 0.7 and state["reteach_count_this_module"] < 2:
        return "reteach"

    # Still animating the five internal phases of the *current* module
    if state["current_timestep"] < 5:
        return "next_timestep"

    modules = state["curriculum"].get("modules") or []
    # On the last module index, go generate the final report instead of advancing “module index”
    if state["current_module"] >= len(modules) - 1:
        return "run_insight"

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
    g.add_node("teacher", teacher_node)
    g.add_node("student_swarm", student_swarm_node)
    g.add_node("peer_contagion", peer_contagion_node)
    g.add_node("assessor", assessor_node)
    g.add_node("reteach_prep", reteach_prep_node)
    g.add_node("bump_timestep", bump_timestep_node)
    g.add_node("advance_module", advance_module_node)
    g.add_node("insight", insight_node)

    # --- Linear “teaching pipeline” for one pass through deliver → students → assess ---
    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "timekeeper")
    g.add_edge("timekeeper", "teacher")
    g.add_edge("teacher", "student_swarm")
    g.add_edge("student_swarm", "peer_contagion")
    g.add_edge("peer_contagion", "assessor")

    # Router: many possible exits from ``assessor``. The string returned by
    # ``route_after_assessor`` chooses *one* outgoing branch.
    g.add_conditional_edges(
        "assessor",
        route_after_assessor,
        {
            "reteach": "reteach_prep",
            "next_timestep": "bump_timestep",
            "advance_module": "advance_module",
            "run_insight": "insight",
        },
    )

    # --- Branches that feed back into the hub (or skip straight to re-delivery) ---
    g.add_edge("reteach_prep", "teacher")  # short-circuit: more teaching, skip timekeeper hub
    # After bumping the clock or changing module, revisit orchestrator so every “round”
    # can start from the same hub (matches CLAUDE.md diagram style).
    g.add_edge("bump_timestep", "orchestrator")
    g.add_edge("advance_module", "orchestrator")
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
        simulation_complete=False,
        insight_report=None,
        current_lesson=None,
        reteach_count_this_module=0,
    )


def run_simulation(initial: ClassroomState) -> ClassroomState:
    """
    Run the whole graph once from ``initial`` until it hits ``END``.

    ``recursion_limit`` is LangGraph’s safety budget: one “step” ≈ visiting one node.
    If it is too low, you get ``GraphRecursionError`` even if your logic is fine — so we
    scale a bit with module count (and re-teach paths add extra visits).
    """
    graph = get_graph()
    n_mod = len(initial["curriculum"].get("modules") or []) or 1
    recursion_limit = max(120, n_mod * 40)
    final = graph.invoke(initial, config={"recursion_limit": recursion_limit})
    return final
