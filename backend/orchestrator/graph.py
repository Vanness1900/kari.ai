"""LangGraph `StateGraph` for the classroom simulation (CLAUDE.md flow sketch)."""

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

GraphRoute = Literal["reteach", "next_timestep", "advance_module", "run_insight"]


def _avg_confusion(state: ClassroomState) -> float:
    levels = [float(s.get("confusion_level", 0.0)) for s in state["students"]]
    return mean(levels) if levels else 0.0


def route_after_assessor(state: ClassroomState) -> GraphRoute:
    """
    Mirrors CLAUDE.md intent: high confusion → re-teach (capped); else timestep/module advance;
    insight only after the last module completes.
    """
    if _avg_confusion(state) > 0.7 and state["reteach_count_this_module"] < 2:
        return "reteach"
    if state["current_timestep"] < 5:
        return "next_timestep"
    modules = state["curriculum"].get("modules") or []
    if state["current_module"] >= len(modules) - 1:
        return "run_insight"
    return "advance_module"


def build_graph():
    g = StateGraph(ClassroomState)
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

    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "timekeeper")
    g.add_edge("timekeeper", "teacher")
    g.add_edge("teacher", "student_swarm")
    g.add_edge("student_swarm", "peer_contagion")
    g.add_edge("peer_contagion", "assessor")

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

    g.add_edge("reteach_prep", "teacher")
    # Next cycle revisits orchestrator hub (CLAUDE.md), then timekeeper + delivery chain.
    g.add_edge("bump_timestep", "orchestrator")
    g.add_edge("advance_module", "orchestrator")
    g.add_edge("insight", END)

    return g.compile()


_compiled_graph = None


def get_graph():
    """Singleton compiled graph (process lifetime)."""
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
    """Default state for invokes and API demos."""
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
    """Execute the compiled graph once; returns terminal state."""
    graph = get_graph()
    # Enough steps for: (5 timesteps * N modules) + re-teaches + orchestration nodes
    n_mod = len(initial["curriculum"].get("modules") or []) or 1
    recursion_limit = max(120, n_mod * 40)
    final = graph.invoke(initial, config={"recursion_limit": recursion_limit})
    return final
