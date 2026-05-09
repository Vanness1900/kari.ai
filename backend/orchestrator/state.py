"""Classroom simulation state carried through LangGraph (see CLAUDE.md)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, NotRequired, TypedDict


class CurriculumModule(TypedDict, total=False):
    id: str
    title: str
    content: str
    blooms_level: int


class CurriculumConfig(TypedDict, total=False):
    title: str
    modules: list[CurriculumModule]


class StudentProfileDict(TypedDict, total=False):
    id: str
    name: str
    learning_style: Literal["visual", "auditory", "reading", "kinesthetic"]
    attention_span_mins: int
    social_anxiety: float
    motivation: float
    peer_influence: float
    knowledge_state: dict[str, float]
    misconceptions: list[str]
    confusion_level: float
    attention_remaining: float
    cumulative_fatigue: float


class TimestepLog(TypedDict, total=False):
    agent: str
    module_index: int
    timestep: int
    payload: dict[str, Any]


class ModuleResult(TypedDict, total=False):
    module_index: int
    student_scores: dict[str, float]
    at_risk_student_ids: list[str]
    notes: str


class InsightReport(TypedDict, total=False):
    summary: str
    curriculum_critique: str
    blooms_alignment_notes: list[str]


class ClassroomState(TypedDict):
    """Graph state — list fields use reducer ``operator.add`` for incremental merges."""

    session_id: str
    curriculum: CurriculumConfig
    students: list[StudentProfileDict]

    current_module: int
    current_timestep: int
    """Timestep 1–5: deliver, process, exercise, assess, update (per CLAUDE.md)."""

    timestep_logs: Annotated[list[TimestepLog], operator.add]
    module_results: Annotated[list[ModuleResult], operator.add]

    simulation_complete: bool
    insight_report: InsightReport | None

    # Teacher output; RAG ingestion of delivery is handled elsewhere later.
    current_lesson: str | None

    # Re-teach cap (CLAUDE.md): max 2 per module before forced advance.
    reteach_count_this_module: int
    avg_confusion_last: NotRequired[float]
