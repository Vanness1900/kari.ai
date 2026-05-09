"""Student swarm: one agent per student (sequential orchestration; stub)."""

from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm.chat import choose_model, llm_json
from orchestrator.state import ClassroomState
from settings import get_settings


def _run_one_student(*, mod: int, step: int, lesson: str, lesson_excerpt: str, model: str, s: dict) -> tuple[dict, dict]:
    sid = s.get("id", "?")
    name = str(s.get("name", "Student"))
    ks = s.get("knowledge_state") or {}
    misconceptions = s.get("misconceptions") or []

    system = (
        "You are a student.\n"
        "You ONLY know the concepts listed in your knowledge_state at the levels provided.\n"
        "When you encounter a concept not in your knowledge_state, you MUST express confusion.\n"
        "Your misconceptions are real beliefs you currently hold.\n\n"
        "Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  \"understood\": boolean,\n'
        '  \"confusion_level\": number,\n'
        '  \"attention_remaining\": number,\n'
        '  \"action\": \"engaged\" | \"confused\" | \"zoned_out\" | \"asked_question\",\n'
        '  \"knowledge_delta\": number,\n'
        '  \"misconception_corrected\": string | null\n'
        "}\n"
    )
    user = (
        f"Module index: {mod}\n"
        f"Timestep: {step}\n\n"
        f"Student name: {name}\n"
        f"Traits: learning_style={s.get('learning_style')} motivation={s.get('motivation')} social_anxiety={s.get('social_anxiety')}\n"
        f"State: confusion_level={s.get('confusion_level')} attention_remaining={s.get('attention_remaining')}\n"
        f"knowledge_state: {ks}\n"
        f"misconceptions: {misconceptions}\n\n"
        f"Teacher lesson text:\n{lesson}\n"
    )

    llm_ok = True
    try:
        out = llm_json(model=model, system=system, user=user)
    except Exception as e:
        llm_ok = False
        out = {
            "understood": step != 4,
            "confusion_level": float(s.get("confusion_level", 0.25)),
            "attention_remaining": float(s.get("attention_remaining", 0.8)),
            "action": "engaged",
            "knowledge_delta": 0.0,
            "misconception_corrected": None,
            "_error": str(e),
        }

    conf = float(out.get("confusion_level", s.get("confusion_level", 0.25)))
    attn = float(out.get("attention_remaining", s.get("attention_remaining", 0.8)))
    s["confusion_level"] = max(0.0, min(1.0, conf))
    s["attention_remaining"] = max(0.0, min(1.0, attn))

    kd = float(out.get("knowledge_delta", 0.0))
    if kd != 0.0 and isinstance(ks, dict) and ks:
        for k in list(ks.keys()):
            ks[k] = max(0.0, min(1.0, float(ks.get(k, 0.0)) + kd * 0.25))
        s["knowledge_state"] = ks

    mastery_vals = [
        float(v)
        for v in (s.get("knowledge_state") or {}).values()
        if isinstance(v, (int, float))
    ]
    mastery_avg = (sum(mastery_vals) / len(mastery_vals)) if mastery_vals else 0.0

    log = {
        "agent": "student",
        "module_index": mod,
        "timestep": step,
        "payload": {
            "student_id": sid,
            "heard_teacher_qna": step == 2,
            "lesson_excerpt": lesson_excerpt,
            "confusion_level": s["confusion_level"],
            "attention_remaining": s["attention_remaining"],
            "knowledge_mastery_avg": mastery_avg,
            "action": out.get("action"),
            "understood": out.get("understood"),
            "knowledge_delta": out.get("knowledge_delta"),
            "model": model,
            "llm_ok": llm_ok,
            "raw": out,
        },
    }
    return s, log


def run_student_swarm(state: ClassroomState) -> dict:
    """
    Run all students for the current timestep. Production: sequential calls, no asyncio.gather
    (rate limits). Stubs copy students and append logs.

    Timestep 2: students react to the teacher's Q&A text in ``current_lesson`` (after ask → answer).
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    lesson = (state.get("current_lesson") or "").strip()
    lesson_excerpt = lesson[:200]
    students = [deepcopy(s) for s in state["students"]]
    logs: list[dict] = []
    settings = get_settings()
    model = choose_model(settings.default_student_model, fallback=settings.default_reasoning_model)

    if settings.enable_parallel_students and len(students) > 1:
        max_workers = max(1, int(settings.max_concurrency))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [
                ex.submit(
                    _run_one_student,
                    mod=mod,
                    step=step,
                    lesson=lesson,
                    lesson_excerpt=lesson_excerpt,
                    model=model,
                    s=s,
                )
                for s in students
            ]
            for fut in as_completed(futures):
                updated, log = fut.result()
                # replace by id
                uid = updated.get("id")
                for i, existing in enumerate(students):
                    if existing.get("id") == uid:
                        students[i] = updated
                        break
                logs.append(log)
    else:
        for s in students:
            updated, log = _run_one_student(
                mod=mod,
                step=step,
                lesson=lesson,
                lesson_excerpt=lesson_excerpt,
                model=model,
                s=s,
            )
            # `updated` is the same dict reference as `s`, but keep the pattern consistent.
            logs.append(log)

    return {"students": students, "timestep_logs": logs}
