"""Assessor agent: compares student profiles step-to-step; optional Gemini LLM assessment."""

from __future__ import annotations

import json
import logging
import re
from statistics import mean

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from orchestrator.state import ClassroomState
from settings import get_settings

logger = logging.getLogger(__name__)

ASSESSOR_SYSTEM_PROMPT = """You are the Assessor Agent in a classroom simulation.

Your job is to compare a student's CURRENT profile vs PREVIOUS profile and produce a concise assessment of learning progress.

Primary signals (only):
1) knowledge_state changes (per concept and overall)
2) misconception changes (resolved, unchanged, new)

Do NOT evaluate or discuss personality, behavior style, motivation, anxiety, or other traits.
Do NOT make psychological or medical assumptions.

Scoring reference:
- knowledge_state values are 0.0 to 1.0
- When reporting percentages, use percentage points on a 0-100 scale (e.g. mastery 0.6 => 60%)

If previous_student_profile is empty or missing keys, treat previous scores as 0 and previous misconceptions as [].

Return STRICT JSON only (no markdown fences, no commentary) using exactly this schema:
{
  "student_id": "string",
  "student_name": "string",
  "overall_progress": {
    "knowledge_avg_previous_pct": 0.0,
    "knowledge_avg_current_pct": 0.0,
    "knowledge_avg_delta_pct_points": 0.0,
    "progress_label": "improved | stable | regressed"
  },
  "concept_changes": [
    {
      "concept": "string",
      "previous_pct": 0.0,
      "current_pct": 0.0,
      "delta_pct_points": 0.0,
      "status": "improved | stable | regressed"
    }
  ],
  "strongest_concepts": ["string"],
  "weakest_concepts": ["string"],
  "most_improved_concepts": ["string"],
  "regressed_concepts": ["string"],
  "misconceptions": {
    "resolved": ["string"],
    "persisting": ["string"],
    "new": ["string"]
  },
  "at_risk": false,
  "summary": "1-3 short sentences focused on learning progress and misconceptions only."
}"""


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _find_prev_snapshot(state: ClassroomState, module_index: int, timestep: int) -> dict[str, dict]:
    latest_in_module: dict[str, dict] | None = None
    latest_any: dict[str, dict] | None = None
    latest_module_step = -1
    latest_any_step = -1

    for log in state["timestep_logs"]:
        if log.get("agent") != "assessor":
            continue
        payload = log.get("payload") or {}
        snap = payload.get("student_profiles_snapshot")
        if not isinstance(snap, dict):
            continue

        log_step = int(log.get("timestep", -1))
        log_module = int(log.get("module_index", -1))
        if log_step >= timestep:
            continue

        if log_step > latest_any_step:
            latest_any_step = log_step
            latest_any = snap
        if log_module == module_index and log_step > latest_module_step:
            latest_module_step = log_step
            latest_in_module = snap

    return latest_in_module or latest_any or {}


def _student_slice_for_prompt(student: dict) -> dict:
    return {
        "id": student.get("id"),
        "name": student.get("name"),
        "knowledge_state": dict(student.get("knowledge_state") or {}),
        "misconceptions": list(student.get("misconceptions") or []),
    }


def _student_change_summary(current_student: dict, prev_student: dict) -> tuple[float, list[str], list[str]]:
    cur_ks = current_student.get("knowledge_state") or {}
    prev_ks = prev_student.get("knowledge_state") or {}
    keys = sorted(set(cur_ks.keys()) | set(prev_ks.keys()))

    deltas: list[float] = []
    for key in keys:
        cur = _to_float(cur_ks.get(key), 0.0)
        prev = _to_float(prev_ks.get(key), 0.0)
        deltas.append(cur - prev)

    avg_delta = mean(deltas) if deltas else 0.0

    cur_m = set(current_student.get("misconceptions") or [])
    prev_m = set(prev_student.get("misconceptions") or [])
    fixed = sorted(prev_m - cur_m)
    new = sorted(cur_m - prev_m)
    return avg_delta, fixed, new


def _parse_llm_json(content: str) -> dict:
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _assess_one_student_llm(
    llm: ChatGoogleGenerativeAI,
    *,
    current_student: dict,
    previous_student: dict,
    module_context: dict,
) -> dict:
    user = f"""current_student_profile:
{json.dumps(_student_slice_for_prompt(current_student), indent=2)}

previous_student_profile:
{json.dumps(previous_student, indent=2)}

module_context:
{json.dumps(module_context, indent=2)}
"""
    messages = [
        SystemMessage(content=ASSESSOR_SYSTEM_PROMPT),
        HumanMessage(content=user),
    ]
    resp = llm.invoke(messages)
    content = resp.content
    if isinstance(content, str):
        raw = content
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        raw = "".join(parts)
    else:
        raw = str(content)
    return _parse_llm_json(raw)


def _run_assessor_llm(state: ClassroomState) -> dict:
    settings = get_settings()
    api_key = (settings.google_api_key or "").strip()
    if not api_key:
        return _run_assessor_deterministic(state)

    mod = state["current_module"]
    step = state["current_timestep"]
    students = state["students"]
    prev_snapshot = _find_prev_snapshot(state, module_index=mod, timestep=step)

    modules = state["curriculum"].get("modules") or []
    mod_meta = modules[mod] if 0 <= mod < len(modules) else {}
    module_context = {
        "module_index": mod,
        "module_id": mod_meta.get("id"),
        "title": mod_meta.get("title"),
        "blooms_level": mod_meta.get("blooms_level"),
        "content_excerpt": (str(mod_meta.get("content") or "")[:800]),
    }

    llm = ChatGoogleGenerativeAI(
        model=settings.default_student_model,
        google_api_key=api_key,
        temperature=0.2,
    )

    student_scores: dict[str, float] = {}
    at_risk_ids: list[str] = []
    per_student_changes: dict[str, dict] = {}
    llm_outputs: dict[str, dict] = {}

    for idx, student in enumerate(students):
        sid = str(student.get("id", idx))
        prev_raw = prev_snapshot.get(sid, {})
        prev_for_prompt = {
            "knowledge_state": dict(prev_raw.get("knowledge_state") or {}),
            "misconceptions": list(prev_raw.get("misconceptions") or []),
        }
        try:
            parsed = _assess_one_student_llm(
                llm,
                current_student=student,
                previous_student=prev_for_prompt,
                module_context=module_context,
            )
        except Exception as e:
            logger.warning("Assessor LLM failed for %s: %s; using deterministic slice", sid, e)
            avg_delta, fixed, new = _student_change_summary(student, prev_raw)
            ks = student.get("knowledge_state") or {}
            vals = [_to_float(v, 0.0) for v in ks.values()]
            score = (mean(vals) if vals else 0.0) * 100.0
            student_scores[sid] = round(score, 2)
            if avg_delta < -0.03 or len(new) > len(fixed):
                at_risk_ids.append(sid)
            per_student_changes[sid] = {
                "knowledge_avg_delta_pct": round(avg_delta * 100.0, 2),
                "misconceptions_fixed": fixed,
                "misconceptions_new": new,
                "llm_error": str(e),
            }
            continue

        llm_outputs[sid] = parsed
        op = parsed.get("overall_progress") or {}
        current_pct = _to_float(op.get("knowledge_avg_current_pct"), 0.0)
        delta_pts = _to_float(op.get("knowledge_avg_delta_pct_points"), 0.0)
        student_scores[sid] = round(current_pct, 2)

        if parsed.get("at_risk") is True or str(op.get("progress_label", "")).lower() == "regressed":
            at_risk_ids.append(sid)

        mc = parsed.get("misconceptions") or {}
        per_student_changes[sid] = {
            "knowledge_avg_delta_pct": round(delta_pts, 2),
            "misconceptions_fixed": list(mc.get("resolved") or []),
            "misconceptions_new": list(mc.get("new") or []),
            "misconceptions_persisting": list(mc.get("persisting") or []),
            "summary": parsed.get("summary"),
            "concept_changes": parsed.get("concept_changes"),
            "strongest_concepts": parsed.get("strongest_concepts"),
            "weakest_concepts": parsed.get("weakest_concepts"),
        }

    confusions = [_to_float(s.get("confusion_level"), 0.0) for s in students]
    avg_c = mean(confusions) if confusions else 0.0
    cohort_delta_pct = mean(
        [c["knowledge_avg_delta_pct"] for c in per_student_changes.values()]
    ) if per_student_changes else 0.0

    snapshot = {
        str(s.get("id", idx)): {
            "knowledge_state": dict(s.get("knowledge_state") or {}),
            "misconceptions": list(s.get("misconceptions") or []),
        }
        for idx, s in enumerate(students)
    }

    updates: dict = {
        "avg_confusion_last": avg_c,
        "timestep_logs": [
            {
                "agent": "assessor",
                "module_index": mod,
                "timestep": step,
                "payload": {
                    "avg_confusion": avg_c,
                    "cohort_knowledge_delta_pct": round(cohort_delta_pct, 2),
                    "per_student_changes": per_student_changes,
                    "student_profiles_snapshot": snapshot,
                    "llm_assessments": llm_outputs,
                    "assessor_mode": "llm",
                },
            }
        ],
    }

    if step >= 5:
        module_note = (
            f"Average knowledge change this step: {round(cohort_delta_pct, 2)}%. "
            f"At-risk students: {len(at_risk_ids)}. (LLM assessor)"
        )
        updates["module_results"] = [
            {
                "module_index": mod,
                "student_scores": student_scores,
                "at_risk_student_ids": at_risk_ids,
                "notes": module_note,
            }
        ]

    return updates


def _run_assessor_deterministic(state: ClassroomState) -> dict:
    mod = state["current_module"]
    step = state["current_timestep"]
    students = state["students"]
    prev_snapshot = _find_prev_snapshot(state, module_index=mod, timestep=step)

    student_scores: dict[str, float] = {}
    at_risk_ids: list[str] = []
    per_student_changes: dict[str, dict] = {}

    for idx, student in enumerate(students):
        sid = str(student.get("id", idx))
        prev = prev_snapshot.get(sid, {})
        avg_delta, fixed, new = _student_change_summary(student, prev)

        ks = student.get("knowledge_state") or {}
        vals = [_to_float(v, 0.0) for v in ks.values()]
        score = (mean(vals) if vals else 0.0) * 100.0
        student_scores[sid] = round(score, 2)

        if avg_delta < -0.03 or len(new) > len(fixed):
            at_risk_ids.append(sid)

        per_student_changes[sid] = {
            "knowledge_avg_delta_pct": round(avg_delta * 100.0, 2),
            "misconceptions_fixed": fixed,
            "misconceptions_new": new,
        }

    confusions = [_to_float(s.get("confusion_level"), 0.0) for s in students]
    avg_c = mean(confusions) if confusions else 0.0
    cohort_delta_pct = mean(
        [c["knowledge_avg_delta_pct"] for c in per_student_changes.values()]
    ) if per_student_changes else 0.0

    snapshot = {
        str(s.get("id", idx)): {
            "knowledge_state": dict(s.get("knowledge_state") or {}),
            "misconceptions": list(s.get("misconceptions") or []),
        }
        for idx, s in enumerate(students)
    }

    updates: dict = {
        "avg_confusion_last": avg_c,
        "timestep_logs": [
            {
                "agent": "assessor",
                "module_index": mod,
                "timestep": step,
                "payload": {
                    "avg_confusion": avg_c,
                    "cohort_knowledge_delta_pct": round(cohort_delta_pct, 2),
                    "per_student_changes": per_student_changes,
                    "student_profiles_snapshot": snapshot,
                    "assessor_mode": "deterministic",
                },
            }
        ],
    }

    if step >= 5:
        module_note = (
            f"Average knowledge change this step: {round(cohort_delta_pct, 2)}%. "
            f"At-risk students: {len(at_risk_ids)}."
        )
        updates["module_results"] = [
            {
                "module_index": mod,
                "student_scores": student_scores,
                "at_risk_student_ids": at_risk_ids,
                "notes": module_note,
            }
        ]

    return updates


def run_assessor(state: ClassroomState) -> dict:
    """
    If ``USE_LLM_ASSESSOR`` is true and ``GOOGLE_API_KEY`` is set, runs sequential
    Gemini assessments per student. Otherwise uses deterministic comparison.
    LLM failures fall back per student or whole batch.
    """
    settings = get_settings()
    if (
        settings.use_llm_assessor
        and (settings.google_api_key or "").strip()
    ):
        try:
            return _run_assessor_llm(state)
        except Exception as e:
            logger.exception("Assessor LLM batch failed: %s", e)
            return _run_assessor_deterministic(state)
    return _run_assessor_deterministic(state)


# Explicit aliases for tests or toggles
run_assessor_with_llm = _run_assessor_llm
run_assessor_deterministic = _run_assessor_deterministic
