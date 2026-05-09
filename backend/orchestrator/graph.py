"""Phase 3: deterministic simulation loop (no LangGraph wiring yet).

Teacher: OpenAI ``gpt-5.5`` only (see ``agents/teacher.py``); stub Markdown if no ``OPENAI_API_KEY``.

Flow per syllabus unit (module):
    timekeeper-ready state → teacher (material + delivery) → student_swarm → advance clock

Timesteps:
  1 deliver — teacher emits module-facing content → students ingest
  2 qna     — clarification / questions (confusion can drop without "re-teach")
  3 exercise
  4 assess
  5 update  — recap / bookkeeping for the module slice

Then advance_module moves to next module_index and resets timestep to 1.
"""

from __future__ import annotations

import copy

from agents.student import apply_agent_output_to_student, run_student_turn
from agents.teacher import current_lesson_for_timestep, generate_timestep_markdown
from orchestrator.state import ClassroomState
from settings import Settings, get_settings


def run_simulation(state: ClassroomState) -> ClassroomState:
    """Runs the coarse loop synchronously until all modules × timesteps are done."""
    s: ClassroomState = copy.deepcopy(dict(state))

    modules = s["curriculum"]["modules"]
    settings = get_settings()

    generated_lessons: dict[tuple[int, int], str] = {}

    while not s["simulation_complete"]:
        s = teacher_step(s, generated_lessons, settings=settings)
        s = student_swarm_step(s, settings=settings)

        route = router_after_swarm(s, num_modules=len(modules))
        s = apply_route(s, route)

    return s


def teacher_step(
    state: ClassroomState,
    generated_lessons: dict[tuple[int, int], str],
    *,
    settings: Settings,
) -> ClassroomState:
    """Teacher: one generated body per (module, timestep); DELIVER text is reused for later phases."""
    mi = state["current_module"]
    t = state["current_timestep"]
    mod = state["curriculum"]["modules"][mi]

    key = (mi, t)
    if key not in generated_lessons:
        deliver = generated_lessons.get((mi, 1)) if t > 1 else None
        generated_lessons[key] = generate_timestep_markdown(
            mod, t, settings=settings, deliver_lesson=deliver
        )

    body = generated_lessons[key]
    state["current_lesson"] = current_lesson_for_timestep(body, t)
    return state


def student_swarm_step(state: ClassroomState, *, settings: Settings) -> ClassroomState:
    """One LLM (or stub) call per student, sequential — never asyncio.gather."""
    mi = state["current_module"]
    t = state["current_timestep"]
    logs = state["timestep_logs"]
    module_title = state["curriculum"]["modules"][mi]["title"]

    for student in state["students"]:
        sid = student["id"]
        out = run_student_turn(
            student,
            current_lesson=state["current_lesson"],
            timestep=t,
            module_title=module_title,
            settings=settings,
        )
        apply_agent_output_to_student(
            student,
            out,
            module_title=module_title,
            timestep=t,
        )

        logs.append(
            {
                "student_id": sid,
                "module_index": mi,
                "timestep": t,
                "action": out["action"],
                "understood": bool(out["understood"]),
                "confusion_level": student["confusion_level"],
                "attention_remaining": student["attention_remaining"],
                "knowledge_delta": float(out["knowledge_delta"]),
            }
        )

    return state


def router_after_swarm(state: ClassroomState, *, num_modules: int) -> str:
    """No explicit re-teach branch: march forward through timestep 1..5, then modules."""
    _ = num_modules  # reserved if you branch on confusion later

    if state["current_timestep"] < 5:
        return "next_timestep"

    if state["current_module"] < num_modules - 1:
        return "advance_module"

    return "finish"


def apply_route(state: ClassroomState, route: str) -> ClassroomState:
    if route == "next_timestep":
        state["current_timestep"] += 1
        return state

    if route == "advance_module":
        state["module_results"].append(
            {
                "module_index": state["current_module"],
                "headline": f"Completed module slice {state['current_module']} (stub).",
            }
        )
        state["current_module"] += 1
        state["current_timestep"] = 1
        return state

    if route == "finish":
        state["module_results"].append(
            {
                "module_index": state["current_module"],
                "headline": f"Completed final module slice {state['current_module']} (stub).",
            }
        )
        state["simulation_complete"] = True
        state["student_assessments"] = state["student_assessments"] or {}
        state.setdefault("timestep_logs", [])
        state.setdefault("module_results", [])
        return state

    raise ValueError(f"Unknown route: {route}")