from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

class ModuleConfig(TypedDict):
    """One unit in the syllabus (expand when your team agrees)."""
    id: str
    title: str
    summary: str
    blooms_level: int  # 1–6 per CLAUDE.md


class CurriculumConfig(TypedDict):
    """Full course configuration passed into the simulation."""
    course_title: str
    modules: list[ModuleConfig]

LearningStyle = Literal["visual", "auditory", "reading", "kinesthetic"]


class StudentProfile(TypedDict):
    id: str
    name: str
    learning_style: LearningStyle
    attention_span_mins: int
    social_anxiety: float
    motivation: float
    peer_influence: float
    knowledge_state: dict[str, float]
    misconceptions: list[str]
    confusion_level: float
    attention_remaining: float
    cumulative_fatigue: float

StudentAction = Literal["engaged", "confused", "zoned_out", "asked_question"]

class TimestepLog(TypedDict):
    """One student's outcome for one timestep."""
    student_id: str
    module_index: int
    timestep: int
    action: StudentAction
    understood: bool
    confusion_level: float
    attention_remaining: float
    knowledge_delta: float


class AssessmentRecord(TypedDict, total=False):
    """Filled after syllabus complete; one dict per student_id."""
    at_risk: bool
    summary: str
    scores: dict[str, float]


class InsightFigure(TypedDict, total=False):
    """Optional visuals referenced by the insight report."""
    id: str  # stable identifier like "fig-1"
    alt: str
    mime_type: str  # e.g. "image/png"
    data_base64: str  # raw base64 bytes (no data: prefix)
    path: str  # optional local path if you later write sidecar files
    url: str  # optional remote URL if you later host somewhere


class InsightReport(TypedDict, total=False):
    """Final curriculum critique."""
    report_markdown: str
    figures: list[InsightFigure]


class ModuleResult(TypedDict, total=False):
    """Aggregate per-module outcome; extend when assessor/graph define it."""
    module_index: int
    headline: str

class ClassroomState(TypedDict):
    session_id: str
    curriculum: CurriculumConfig
    students: list[StudentProfile]

    current_module: int
    # 1=deliver 2=qna 3=exercise 4=assess 5=update (per module, then advance_module)
    current_timestep: int

    current_lesson: str | None

    timestep_logs: list[TimestepLog]
    module_results: list[ModuleResult]
    student_assessments: dict[str, AssessmentRecord] | None
    simulation_complete: bool
    insight_report: InsightReport | None


KNOWLEDGE_GATE_INSTRUCTION = """
You are a student. You ONLY know the concepts listed in your knowledge_state
at the levels provided. You have NOT been taught anything outside this list.

When you encounter a concept not in your knowledge_state, you MUST express
confusion — do not infer or invent understanding you have not earned yet.

Your misconceptions are real beliefs you currently hold. Do not abandon them
unless the lesson directly corrects them.
"""


def blank_classroom_state(session_id: str = "session_dev") -> ClassroomState:
    """Toy state for Phase 1; LangGraph nodes will mutate this later."""
    curriculum: CurriculumConfig = {
        "course_title": "Intro Demo",
        "modules": [
            {
                "id": "m0",
                "title": "Vectors",
                "summary": "What a vector is, components, intuition only.",
                "blooms_level": 2,
            },
            {
                "id": "m1",
                "title": "Dot product",
                "summary": "Definition geometric and algebraic.",
                "blooms_level": 3,
            },
        ],
    }

    students: list[StudentProfile] = [
        {
            "id": "stu_001",
            "name": "Avery",
            "learning_style": "visual",
            "attention_span_mins": 18,
            "social_anxiety": 0.3,
            "motivation": 0.8,
            "peer_influence": 0.4,
            "knowledge_state": {"Vectors": 0.2},
            "misconceptions": ["Vectors are arrows with fixed position in space"],
            "confusion_level": 0.2,
            "attention_remaining": 1.0,
            "cumulative_fatigue": 0.0,
        },
        {
            "id": "stu_002",
            "name": "Jordan",
            "learning_style": "reading",
            "attention_span_mins": 22,
            "social_anxiety": 0.6,
            "motivation": 0.5,
            "peer_influence": 0.7,
            "knowledge_state": {"Vectors": 0.0},
            "misconceptions": [],
            "confusion_level": 0.5,
            "attention_remaining": 0.9,
            "cumulative_fatigue": 0.0,
        },
    ]

    return {
        "session_id": session_id,
        "curriculum": curriculum,
        "students": students,
        "current_module": 0,
        "current_timestep": 1,
        "current_lesson": None,
        "timestep_logs": [],
        "module_results": [],
        "student_assessments": None,
        "simulation_complete": False,
        "insight_report": None,
    }