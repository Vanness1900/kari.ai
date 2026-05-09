"""Single-student agent — Gemini JSON in, profile + log fields out. No RAG."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from orchestrator.state import KNOWLEDGE_GATE_INSTRUCTION, StudentAction, StudentProfile
from settings import Settings

logger = logging.getLogger(__name__)

# Lean prompts (~CLAUDE.md student token budget).
_SYSTEM_BASE = (
    "You simulate ONE learner in a classroom sim. Reply with a single JSON object only, "
    "no markdown fences, no extra text. Your behaviour must follow the knowledge gate: "
    "you only know what knowledge_state lists; do not use outside physics/math facts. "
    "Confusion_level and attention_remaining are floats in [0, 1]. "
    'action must be exactly one of: "engaged", "confused", "zoned_out", "asked_question". '
    "knowledge_delta is a small float in [-0.2, 0.2] for this timestep. "
)

_PHASE_HINT: dict[int, str] = {
    1: "Lesson delivery — you listen; you may zone out if attention is low.",
    2: "Q&A — you may use asked_question if anxious but curious; else engaged or confused.",
    3: "Exercise — try to apply; confusion may rise if stuck.",
    4: "Assessment — no references; test what you actually know.",
    5: "Update — consolidation; brief reflection.",
}


def run_student_turn(
    student: StudentProfile,
    *,
    current_lesson: str | None,
    timestep: int,
    module_title: str,
    settings: Settings,
) -> dict[str, Any]:
    """Return parsed agent output: understood, confusion_level, attention_remaining, action, knowledge_delta."""
    lesson = current_lesson or ""
    if settings.google_api_key:
        try:
            return _invoke_gemini(student, lesson, timestep, module_title, settings)
        except Exception:
            logger.exception("Student LLM failed for %s; using stub.", student.get("id"))
    return _stub_turn(student, timestep)


def _invoke_gemini(
    student: StudentProfile,
    lesson: str,
    timestep: int,
    module_title: str,
    settings: Settings,
) -> dict[str, Any]:
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.default_student_model,
        google_api_key=settings.google_api_key,
        temperature=0.7,
    )
    phase = _PHASE_HINT.get(timestep, "Participate.")
    system = _SYSTEM_BASE + KNOWLEDGE_GATE_INSTRUCTION.strip()
    human = HumanMessage(
        content=(
            f"timestep={timestep}\n"
            f"module={module_title}\n"
            f"phase_hint={phase}\n\n"
            f"student_profile_json={json.dumps(_student_payload(student))}\n\n"
            f"current_lesson_markdown:\n{lesson}\n\n"
            'Return JSON: {"understood": bool, "confusion_level": float, '
            '"attention_remaining": float, "action": str, "knowledge_delta": float}'
        )
    )
    out = llm.invoke([SystemMessage(content=system), human])
    text = (out.content or "").strip()
    return _parse_student_json(text, student, timestep)


def _student_payload(student: StudentProfile) -> dict[str, Any]:
    return {
        "id": student["id"],
        "name": student["name"],
        "learning_style": student["learning_style"],
        "attention_span_mins": student["attention_span_mins"],
        "social_anxiety": student["social_anxiety"],
        "motivation": student["motivation"],
        "peer_influence": student["peer_influence"],
        "knowledge_state": student["knowledge_state"],
        "misconceptions": student["misconceptions"],
        "confusion_level": student["confusion_level"],
        "attention_remaining": student["attention_remaining"],
        "cumulative_fatigue": student["cumulative_fatigue"],
    }


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_student_json(raw: str, student: StudentProfile, timestep: int) -> dict[str, Any]:
    m = _JSON_FENCE.search(raw)
    payload = m.group(1).strip() if m else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Bad student JSON for %s @ t=%s — stub.", student["id"], timestep)
        return _stub_turn(student, timestep)

    # Validate / clamp
    action = data.get("action", "engaged")
    if action not in ("engaged", "confused", "zoned_out", "asked_question"):
        action = "engaged"

    return {
        "understood": bool(data.get("understood", False)),
        "confusion_level": _clamp01(float(data.get("confusion_level", 0.5))),
        "attention_remaining": _clamp01(float(data.get("attention_remaining", 0.5))),
        "action": action,
        "knowledge_delta": float(data.get("knowledge_delta", 0.0)),
    }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _stub_turn(student: StudentProfile, t: int) -> dict[str, Any]:
    """Deterministic behaviour when no API key (matches prior graph.py heuristics)."""
    if t == 1:
        k_delta = 0.05 + 0.01 * student["motivation"]
        confused = _clamp01(student["confusion_level"] - 0.05)
        understood = student["motivation"] > 0.45
        action: StudentAction = "engaged"
    elif t == 2:
        k_delta = 0.03
        confused = max(0.0, student["confusion_level"] - 0.10)
        if student["social_anxiety"] > 0.55 and confused > 0.35:
            action = "confused"
        else:
            action = "asked_question"
            confused *= 0.85
        understood = confused < 0.5
    elif t == 3:
        if student["attention_remaining"] < 0.35:
            action = "zoned_out"
            k_delta = 0.01
            confused = min(1.0, student["confusion_level"] + 0.06)
            understood = False
        else:
            action = "engaged"
            k_delta = 0.06 + 0.02 * student["motivation"]
            confused = max(0.0, student["confusion_level"] - 0.03)
            understood = True
    elif t == 4:
        k_delta = 0.02
        understood = student["confusion_level"] < 0.45 or student["motivation"] > 0.65
        action = "engaged" if understood else "confused"
        confused = student["confusion_level"]
        if not understood:
            confused = min(1.0, confused + 0.05)
    else:  # t == 5
        k_delta = 0.03
        confused = student["confusion_level"]
        action = "engaged"
        understood = confused < 0.55

    return {
        "understood": understood,
        "confusion_level": confused,
        "attention_remaining": student["attention_remaining"],
        "action": action,
        "knowledge_delta": k_delta,
    }


def apply_agent_output_to_student(
    student: StudentProfile,
    out: dict[str, Any],
    *,
    module_title: str,
    timestep: int,
) -> None:
    """Mutate profile from agent output; adjust knowledge_state from delta."""
    student["confusion_level"] = _clamp01(float(out["confusion_level"]))
    student["attention_remaining"] = _clamp01(float(out["attention_remaining"]))

    base_energy = 0.06
    student["attention_remaining"] = _clamp01(student["attention_remaining"] - base_energy)
    if timestep == 5:
        student["cumulative_fatigue"] = min(
            1.0, student.get("cumulative_fatigue", 0.0) + 0.05
        )

    delta = float(out.get("knowledge_delta", 0.0))
    ks = student["knowledge_state"]
    if not ks:
        ks[module_title] = 0.0
    n = len(ks)
    per = delta / max(1, n)
    for key in list(ks.keys()):
        ks[key] = _clamp01(ks[key] + per)
