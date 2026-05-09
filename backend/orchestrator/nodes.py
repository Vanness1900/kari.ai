"""LangGraph node callables — thin wrappers around `agents.*` + small state mutators."""

from __future__ import annotations

import os

from agents.assessor import run_assessor
from agents.insight import run_insight
from agents.peer import run_peer_contagion
from agents.stats import run_stats
from agents.student import run_student_swarm
from agents.student_questions import run_student_questions
from agents.teacher import run_teacher
from agents.timekeeper import run_timekeeper
from orchestrator.state import ClassroomState


def _trace(node: str, state: ClassroomState, extra: dict | None = None) -> None:
    if os.getenv("KARIAI_TRACE", "").strip() not in {"1", "true", "TRUE", "yes", "YES"}:
        return
    mod = state.get("current_module")
    step = state.get("current_timestep")
    msg = f"[trace] node={node} module={mod} timestep={step}"
    if extra:
        msg += f" extra={extra}"
    print(msg, flush=True)


def orchestrator_node(state: ClassroomState) -> dict:
    """Route / setup step; extend with module gating and caps."""
    _trace("orchestrator", state)
    return {
        "timestep_logs": [
            {
                "agent": "orchestrator",
                "module_index": state["current_module"],
                "timestep": state["current_timestep"],
                "payload": {"stub": True},
            }
        ],
    }


def timekeeper_node(state: ClassroomState) -> dict:
    _trace("timekeeper", state)
    return run_timekeeper(state)


def student_questions_node(state: ClassroomState) -> dict:
    _trace("student_questions", state)
    return run_student_questions(state)


def teacher_node(state: ClassroomState) -> dict:
    _trace("teacher", state)
    return run_teacher(state)


def student_swarm_node(state: ClassroomState) -> dict:
    _trace("student_swarm", state, {"n_students": len(state.get("students") or [])})
    return run_student_swarm(state)


def peer_contagion_node(state: ClassroomState) -> dict:
    _trace("peer_contagion", state)
    return run_peer_contagion(state)


def stats_node(state: ClassroomState) -> dict:
    _trace("stats", state)
    return run_stats(state)


def assessor_node(state: ClassroomState) -> dict:
    """End-of-course assessor phase: one student per invocation."""
    _trace("assessor_phase", state, {"assessor_index": int(state.get("assessor_index", 0))})
    return run_assessor(state)


def insight_node(state: ClassroomState) -> dict:
    _trace("insight", state)
    return run_insight(state)


def bump_timestep_node(state: ClassroomState) -> dict:
    return {"current_timestep": state["current_timestep"] + 1}


def advance_module_node(state: ClassroomState) -> dict:
    return {
        "current_module": state["current_module"] + 1,
        "current_timestep": 1,
        "module_delivery_snapshot": None,
        "qna_student_questions": [],
        # Assessor is a post-course phase; reset progress for safety when module advances.
        "assessor_index": 0,
        "student_assessments": None,
    }
