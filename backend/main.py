"""FastAPI entrypoint — API + orchestration bootstrap (runs from ``backend/`` cwd)."""

from __future__ import annotations

import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from orchestrator.graph import (
    blank_classroom_state,
    run_simulation,
    run_simulation_streaming,
)
from orchestrator.state import ClassroomState
from settings import get_settings
from storage.session import list_sessions, load_session, save_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_data_dirs()
    yield


app = FastAPI(title="kari.ai backend", lifespan=lifespan)
_settings = get_settings()

_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Simulation start (async via BackgroundTasks)
# ---------------------------------------------------------------------------


_LEARNING_STYLES = ["visual", "auditory", "reading", "kinesthetic"]
_FIRST_NAMES = [
    "Aiden", "Bea", "Cara", "Devi", "Ezra", "Fen", "Gita", "Hugo",
    "Iris", "Jules", "Kai", "Lin", "Mira", "Nilesh", "Oren", "Pia",
    "Quinn", "Rui", "Sana", "Theo", "Uma", "Vik", "Wen", "Xio",
    "Yara", "Zoe",
]


class StartRequest(BaseModel):
    """Frontend payload — generous defaults so the demo runs with no body."""

    session_name: str | None = Field(default=None)
    curriculum_text: str | None = Field(default=None)
    content_text: str | None = Field(default=None)
    vision_mission: str | None = Field(default=None)
    target_students_description: str | None = Field(default=None)
    bloom_levels: list[str] = Field(default_factory=list)
    total_students: int = Field(default=5, ge=1, le=50)
    n_modules: int = Field(default=2, ge=1, le=8)


def _new_session_id() -> str:
    return "session_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _synth_modules(req: StartRequest) -> list[dict[str, Any]]:
    text = (req.curriculum_text or "").strip() or "Introductory module — pacing and structure under test."
    extra = (req.content_text or "").strip()
    bloom_idx = {b.lower(): i + 1 for i, b in enumerate(["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"])}
    levels = [bloom_idx.get(b.lower(), 2) for b in (req.bloom_levels or [])] or [2]

    modules: list[dict[str, Any]] = []
    n = max(1, req.n_modules)
    for i in range(n):
        share = text if i == 0 else extra or text
        modules.append(
            {
                "id": f"m{i}",
                "title": f"Module {i + 1}" if not req.session_name else f"{req.session_name} — Module {i + 1}",
                "content": share,
                "blooms_level": levels[i % len(levels)],
            }
        )
    return modules


def _synth_students(req: StartRequest) -> list[dict[str, Any]]:
    rng = random.Random(42)
    out: list[dict[str, Any]] = []
    for i in range(req.total_students):
        name = _FIRST_NAMES[i % len(_FIRST_NAMES)]
        out.append(
            {
                "id": f"stu_{i + 1}",
                "name": f"{name}{i // len(_FIRST_NAMES) + 1 if i >= len(_FIRST_NAMES) else ''}",
                "learning_style": _LEARNING_STYLES[i % len(_LEARNING_STYLES)],
                "attention_span_mins": rng.randint(8, 25),
                "social_anxiety": round(rng.random(), 2),
                "motivation": round(0.4 + rng.random() * 0.6, 2),
                "peer_influence": round(rng.random(), 2),
                "knowledge_state": {"intro": round(rng.random() * 0.3, 2)},
                "misconceptions": [],
                "confusion_level": round(0.15 + rng.random() * 0.25, 2),
                "attention_remaining": round(0.7 + rng.random() * 0.3, 2),
                "cumulative_fatigue": 0.0,
            }
        )
    return out


def _build_initial(req: StartRequest, session_id: str) -> ClassroomState:
    curriculum = {
        "title": (req.session_name or "Untitled curriculum").strip() or "Untitled curriculum",
        "modules": _synth_modules(req),
    }
    students = _synth_students(req)
    return blank_classroom_state(session_id, curriculum=curriculum, students=students)


def _run_with_persistence(initial: ClassroomState) -> None:
    """Background-task entrypoint. Errors are written into the session file so the UI sees them."""
    sid = initial["session_id"]
    try:
        run_simulation_streaming(initial)
    except Exception as exc:
        existing = load_session(sid) or dict(initial)
        existing["simulation_error"] = repr(exc)
        existing["simulation_complete"] = True  # unblock the UI from spinning forever
        try:
            save_session(sid, existing)
        except Exception:
            pass


@app.post("/api/simulation/start")
def start_simulation(
    background_tasks: BackgroundTasks,
    body: StartRequest | None = None,
    include_state: bool = Query(default=False),
):
    """Kick off a non-blocking run; returns immediately with a poll-able ``session_id``."""
    req = body or StartRequest()
    session_id = _new_session_id()
    initial = _build_initial(req, session_id)
    save_session(session_id, initial)

    background_tasks.add_task(_run_with_persistence, initial)

    payload: dict[str, Any] = {
        "status": "running",
        "session_id": session_id,
        "students_count": len(initial["students"]),
        "n_modules": len(initial["curriculum"].get("modules") or []),
    }
    if include_state:
        payload["initial_state"] = initial
    return payload


# ---------------------------------------------------------------------------
# Simulation status / state / events (read from session JSON)
# ---------------------------------------------------------------------------


def _require_session(session_id: str) -> dict[str, Any]:
    state = load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown session_id: {session_id}")
    return state


@app.get("/api/simulation/status")
def simulation_status(id: str = Query(..., description="session_id from /api/simulation/start")):
    """Cheap projection for the live UI's polling tick."""
    s = _require_session(id)
    logs = s.get("timestep_logs") or []
    last_event_at = logs[-1].get("payload", {}).get("at") if logs else None
    return {
        "session_id": s.get("session_id", id),
        "current_module": s.get("current_module"),
        "current_timestep": s.get("current_timestep"),
        "students_count": len(s.get("students") or []),
        "log_count": len(logs),
        "simulation_complete": bool(s.get("simulation_complete")),
        "has_insight": s.get("insight_report") is not None,
        "has_error": "simulation_error" in s,
        "avg_confusion_last": s.get("avg_confusion_last"),
        "last_event_at": last_event_at,
    }


@app.get("/api/simulation/state")
def simulation_state(id: str = Query(...)):
    """Full ``ClassroomState`` snapshot. Heavier — fetch only when a phase advances."""
    return _require_session(id)


@app.get("/api/simulation/events")
def simulation_events(
    id: str = Query(...),
    since: int = Query(default=0, ge=0, description="Index into timestep_logs to start from"),
    limit: int = Query(default=200, ge=1, le=2000),
):
    """Sliced view of ``timestep_logs`` for incremental polling."""
    s = _require_session(id)
    logs = s.get("timestep_logs") or []
    total = len(logs)
    end = min(total, since + limit)
    return {
        "session_id": s.get("session_id", id),
        "since": since,
        "next_since": end,
        "total": total,
        "events": logs[since:end],
        "simulation_complete": bool(s.get("simulation_complete")),
    }


@app.get("/api/sessions")
def sessions_index():
    return {"sessions": list_sessions()}


@app.get("/api/insight-image/{session_id}/{filename}")
def get_insight_image(session_id: str, filename: str):
    """
    Serve GPT Image 2 insight report images.

    Images are generated to: uploads/insight_reports/{session_id}/{filename}
    """
    if not session_id or not filename:
        raise HTTPException(status_code=404, detail="Not found")
    if any(part in filename for part in ("..", "/", "\\")):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.lower().endswith(".png"):
        raise HTTPException(status_code=404, detail="Not found")

    settings = get_settings()
    base_dir = (settings.uploads_path / "insight_reports" / session_id).resolve()
    file_path = (base_dir / filename).resolve()
    if base_dir not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(path=str(file_path), media_type="image/png")


@app.get("/api/report/{session_id}")
def get_report(session_id: str, request: Request):
    s = _require_session(session_id)
    if not s.get("simulation_complete"):
        raise HTTPException(status_code=409, detail="Simulation has not finished yet.")

    report = s.get("insight_report")
    if isinstance(report, dict):
        images = report.get("visual_report_images")
        if isinstance(images, list):
            base = str(request.base_url).rstrip("/")
            urls: list[str] = []
            for p in images:
                name = Path(str(p)).name
                if not name:
                    continue
                urls.append(f"{base}/api/insight-image/{session_id}/{name}")
            report = {**report, "visual_report_images": urls}

    return {
        "session_id": s.get("session_id", session_id),
        "insight_report": report,
        "student_assessments": s.get("student_assessments") or {},
        "module_results": s.get("module_results") or [],
        "students": s.get("students") or [],
        "curriculum": s.get("curriculum") or {},
        "timestep_logs": s.get("timestep_logs") or [],
        "simulation_error": s.get("simulation_error"),
    }


# ---------------------------------------------------------------------------
# Dev / debug
# ---------------------------------------------------------------------------


@app.post("/api/simulation/debug/run")
def debug_run_simulation():
    """Synchronous, returns the entire final state. For local debugging only."""
    state = blank_classroom_state("session_debug")
    final = run_simulation(state)
    return final
