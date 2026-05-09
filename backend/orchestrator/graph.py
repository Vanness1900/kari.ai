"""Phase 3: deterministic simulation loop (no LangGraph wiring yet).

Teacher: calls Gemini when ``GOOGLE_API_KEY`` is set (see ``agents/teacher.py``); else stub Markdown.

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

from agents.teacher import generate_module_markdown
from orchestrator.state import ClassroomState
from settings import Settings, get_settings


def run_simulation(state: ClassroomState) -> ClassroomState:
    """Runs the coarse loop synchronously until all modules × timesteps are done."""
    s: ClassroomState = copy.deepcopy(dict(state))

    modules = s["curriculum"]["modules"]
    settings = get_settings()

    generated_for_module_idx: dict[int, str] = {}

    while not s["simulation_complete"]:
        s = teacher_step(s, generated_for_module_idx, settings=settings)
        s = student_swarm_step(s)

        route = router_after_swarm(s, num_modules=len(modules))
        s = apply_route(s, route)

    return s


def teacher_step(
    state: ClassroomState,
    generated_for_module_idx: dict[int, str],
    *,
    settings: Settings,
) -> ClassroomState:
    """Teacher: generate-once-per-module stored in generated_for_module_idx; reflect in current_lesson each timestep."""
    mi = state["current_module"]
    t = state["current_timestep"]
    mod = state["curriculum"]["modules"][mi]

    if mi not in generated_for_module_idx:
        generated_for_module_idx[mi] = generate_module_markdown(mod, settings=settings)

    body = generated_for_module_idx[mi]

    phase = {1: "DELIVER", 2: "QNA", 3: "EXERCISE", 4: "ASSESS", 5: "UPDATE"}[t]
    state["current_lesson"] = f"[{phase} | timestep {t}/5]\n\n{body}"
    return state


def student_swarm_step(state: ClassroomState) -> ClassroomState:
    """Sequential faux students — preserves 'no asyncio.gather' discipline for later."""
    mi = state["current_module"]
    t = state["current_timestep"]
    logs = state["timestep_logs"]

    for student in state["students"]:
        sid = student["id"]

        if t == 1:
            k_delta = 0.05 + 0.01 * student["motivation"]
            student["confusion_level"] = max(0.0, student["confusion_level"] - 0.05)
            understood = student["motivation"] > 0.45
            action = "engaged"
        elif t == 2:
            # qna tends to shave confusion slightly; sometimes a question fires
            k_delta = 0.03
            student["confusion_level"] = max(0.0, student["confusion_level"] - 0.10)
            if student["social_anxiety"] > 0.55 and student["confusion_level"] > 0.35:
                action = "confused"
            else:
                action = "asked_question"
                student["confusion_level"] *= 0.85
            understood = student["confusion_level"] < 0.5
        elif t == 3:
            if student["attention_remaining"] < 0.35:
                action = "zoned_out"
                k_delta = 0.01
                student["confusion_level"] = min(1.0, student["confusion_level"] + 0.06)
                understood = False
            else:
                action = "engaged"
                k_delta = 0.06 + 0.02 * student["motivation"]
                student["confusion_level"] = max(0.0, student["confusion_level"] - 0.03)
                understood = True
        elif t == 4:
            k_delta = 0.02
            understood = student["confusion_level"] < 0.45 or student["motivation"] > 0.65
            action = "engaged" if understood else "confused"
            if not understood:
                student["confusion_level"] = min(1.0, student["confusion_level"] + 0.05)
        else:  # 5 update
            k_delta = 0.03
            student["cumulative_fatigue"] = min(1.0, student["cumulative_fatigue"] + 0.05)
            action = "engaged"
            understood = student["confusion_level"] < 0.55

        for key in list(student["knowledge_state"].keys()):
            student["knowledge_state"][key] = min(
                1.0, student["knowledge_state"][key] + k_delta
            )

        student["attention_remaining"] = max(0.0, student["attention_remaining"] - 0.06)

        logs.append(
            {
                "student_id": sid,
                "module_index": mi,
                "timestep": t,
                "action": action,
                "understood": understood,
                "confusion_level": student["confusion_level"],
                "attention_remaining": student["attention_remaining"],
                "knowledge_delta": k_delta,
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