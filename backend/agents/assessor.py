"""Assessor agent: end-of-course per-student assessment (stub)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from llm.chat import llm_text
from orchestrator.state import ClassroomState
from settings import get_settings


def _assess_one(*, state: ClassroomState, idx: int, model: str) -> tuple[str, dict, dict]:
    students = state["students"]
    s = students[idx]
    sid = str(s.get("id", idx))
    name = str(s.get("name", "Student"))

    student_logs = [
        l
        for l in (state.get("timestep_logs") or [])
        if l.get("agent") == "student" and (l.get("payload") or {}).get("student_id") == sid
    ]
    ks = s.get("knowledge_state") or {}

    system = (
        "You are an assessor evaluating ONE student's learning arc across a simulated course. "
        "Be concrete and concise. Output plain text."
    )
    user = (
        f"Student: {name} ({sid})\n"
        f"Final student state:\n{s}\n\n"
        f"Student timestep logs (chronological):\n{student_logs}\n\n"
        "Return:\n"
        "- Overall score 0.0-1.0 (estimate)\n"
        "- 0-3 risk flags\n"
        "- 4-8 sentence narrative of progress, misconceptions, and where they struggled\n"
        "Format:\n"
        "SCORE: <float>\n"
        "FLAGS: <comma-separated or none>\n"
        "NARRATIVE: <text>\n"
    )

    llm_ok = True
    try:
        text = llm_text(model=model, system=system, user=user)
    except Exception as e:
        llm_ok = False
        nums = [float(v) for v in ks.values() if isinstance(v, (int, float))]
        overall = sum(nums) / len(nums) if nums else 0.5
        risk_flags = []
        if float(s.get("confusion_level", 0.0)) > 0.65:
            risk_flags.append("high_confusion")
        if float(s.get("attention_remaining", 1.0)) < 0.25:
            risk_flags.append("low_attention")
        text = f"SCORE: {overall:.2f}\nFLAGS: {','.join(risk_flags) or 'none'}\nNARRATIVE: [stub-fallback] LLM error: {e}"

    score = 0.5
    flags: list[str] = []
    narrative = text.strip()
    for line in text.splitlines():
        if line.startswith("SCORE:"):
            try:
                score = float(line.split("SCORE:", 1)[1].strip())
            except Exception:
                pass
        if line.startswith("FLAGS:"):
            raw = line.split("FLAGS:", 1)[1].strip()
            if raw and raw.lower() != "none":
                flags = [f.strip() for f in raw.split(",") if f.strip()]
        if line.startswith("NARRATIVE:"):
            narrative = line.split("NARRATIVE:", 1)[1].strip()

    record = {
        "student_id": sid,
        "overall_score": max(0.0, min(1.0, float(score))),
        "risk_flags": flags,
        "narrative": narrative,
    }
    log = {
        "agent": "assessor",
        "module_index": state["current_module"],
        "timestep": state["current_timestep"],
        "payload": {"student_id": sid, "assessor_index": idx, "model": model, "llm_ok": llm_ok},
    }
    return sid, record, log


def run_assessor(state: ClassroomState) -> dict:
    """
    End-of-course assessor phase.

    Runs once per student, after all modules/timesteps complete.
    If ENABLE_PARALLEL_ASSESSOR is set, assessments run with bounded concurrency.
    """
    settings = get_settings()
    model = settings.default_reasoning_model
    existing = state.get("student_assessments") or {}
    merged = dict(existing)
    logs: list[dict] = []

    n = len(state["students"])
    if settings.enable_parallel_assessor and n > 1:
        max_workers = max(1, int(settings.max_concurrency))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_assess_one, state=state, idx=i, model=model) for i in range(n)]
            for fut in as_completed(futures):
                sid, record, log = fut.result()
                merged[sid] = record
                logs.append(log)
    else:
        for i in range(n):
            sid, record, log = _assess_one(state=state, idx=i, model=model)
            merged[sid] = record
            logs.append(log)

    return {"student_assessments": merged, "assessor_index": n, "timestep_logs": logs}
