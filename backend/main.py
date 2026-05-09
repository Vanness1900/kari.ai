"""FastAPI entrypoint — API + orchestration bootstrap (runs from ``backend/`` cwd)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.graph import blank_classroom_state, run_simulation
from settings import get_settings


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


@app.post("/api/simulation/start")
def start_simulation():
    """Temporary stub runner — replaces with LangGraph BackgroundTasks + persistence later."""
    state = blank_classroom_state("session_stub")
    final = run_simulation(state)
    return {
        "status": "completed",
        "session_id": final["session_id"],
        "simulation_complete": final["simulation_complete"],
        "module_results_count": len(final["module_results"]),
        "logs_count": len(final["timestep_logs"]),
        "has_insight": final["insight_report"] is not None,
    }

