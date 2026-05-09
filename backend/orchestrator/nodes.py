"""LangGraph node callables — thin wrappers around `agents.*` + small state mutators."""

from __future__ import annotations

from agents.assessor import run_assessor
from agents.insight import run_insight
from agents.peer import run_peer_contagion
from agents.student import run_student_swarm
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


def teacher_node(state: ClassroomState) -> dict:
    return run_teacher(state)


def student_swarm_node(state: ClassroomState) -> dict:
    return run_student_swarm(state)


def peer_contagion_node(state: ClassroomState) -> dict:
    return run_peer_contagion(state)


def assessor_node(state: ClassroomState) -> dict:
    return run_assessor(state)


def insight_node(state: ClassroomState) -> dict:
    return run_insight(state)


def reteach_prep_node(state: ClassroomState) -> dict:
    return {"reteach_count_this_module": state["reteach_count_this_module"] + 1}


def bump_timestep_node(state: ClassroomState) -> dict:
    return {"current_timestep": state["current_timestep"] + 1}


def advance_module_node(state: ClassroomState) -> dict:
    return {
        "current_module": state["current_module"] + 1,
        "current_timestep": 1,
        "reteach_count_this_module": 0,
    }
