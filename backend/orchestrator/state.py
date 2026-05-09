"""Classroom simulation state carried through LangGraph (see CLAUDE.md)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from typing_extensions import NotRequired


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


class AssessmentRecord(TypedDict, total=False):
    student_id: str
    overall_score: float
    risk_flags: list[str]
    narrative: str


class ClassroomState(TypedDict):
    """Graph state — list fields use reducer ``operator.add`` for incremental merges."""

    session_id: str
    curriculum: CurriculumConfig
    students: list[StudentProfileDict]

    current_module: int
    current_timestep: int
    """Timestep 1–5: deliver, qna, exercise, assess, update."""

    timestep_logs: Annotated[list[TimestepLog], operator.add]
    module_results: Annotated[list[ModuleResult], operator.add]

    # Post-simulation: one assessment record per student (filled sequentially in assessor phase).
    student_assessments: dict[str, AssessmentRecord] | None
    assessor_index: int

    simulation_complete: bool
    insight_report: InsightReport | None

    # Teacher output; RAG ingestion of delivery is handled elsewhere later.
    current_lesson: str | None

    # Timestep 1 delivery copy — students ask against this on phase 2 (QNA); teacher answers in Q&A form.
    module_delivery_snapshot: str | None
    # Filled by ``student_questions`` node (timestep 2), consumed by teacher, then students react to ``current_lesson``.
    qna_student_questions: list[dict[str, Any]]

    avg_confusion_last: NotRequired[float]
