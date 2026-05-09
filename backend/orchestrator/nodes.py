"""LangGraph node callables — thin wrappers around `agents.*` + small state mutators."""

from __future__ import annotations

from agents.assessor import run_assessor
from agents.insight import run_insight
from agents.peer import run_peer_contagion
from agents.stats import run_stats
from agents.student import run_student_swarm
from agents.student_questions import run_student_questions
from agents.teacher import run_teacher
from agents.timekeeper import run_timekeeper
from orchestrator.state import ClassroomState


def orchestrator_node(state: ClassroomState) -> dict:
    """Route / setup step; extend with module gating and caps."""
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
    return run_timekeeper(state)


def student_questions_node(state: ClassroomState) -> dict:
    return run_student_questions(state)


def teacher_node(state: ClassroomState) -> dict:
    return run_teacher(state)


def student_swarm_node(state: ClassroomState) -> dict:
    return run_student_swarm(state)


def peer_contagion_node(state: ClassroomState) -> dict:
    return run_peer_contagion(state)


def stats_node(state: ClassroomState) -> dict:
    return run_stats(state)


def assessor_node(state: ClassroomState) -> dict:
    """End-of-course assessor phase: one student per invocation."""
    return run_assessor(state)


def insight_node(state: ClassroomState) -> dict:
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
