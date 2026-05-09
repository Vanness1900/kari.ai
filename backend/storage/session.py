"""Atomic session-state JSON storage. One file per session id under ``settings.sessions_path``."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from settings import get_settings


def _safe_id(session_id: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
    return "".join(c for c in session_id if c in keep) or "session"


def session_path(session_id: str) -> Path:
    base = get_settings().sessions_path
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{_safe_id(session_id)}.json"


def save_session(session_id: str, state: Mapping[str, Any]) -> Path:
    """Atomic write so concurrent readers (the polling frontend) never see a torn file."""
    path = session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, default=str)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path


def load_session(session_id: str) -> dict[str, Any] | None:
    path = session_path(session_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def list_sessions() -> list[dict[str, Any]]:
    """Newest-first listing of saved sessions."""
    base = get_settings().sessions_path
    if not base.exists():
        return []
    entries: list[tuple[float, str, Path]] = []
    for p in base.glob("*.json"):
        try:
            entries.append((p.stat().st_mtime, p.stem, p))
        except OSError:
            continue
    entries.sort(reverse=True)
    out: list[dict[str, Any]] = []
    for mtime, sid, p in entries:
        meta: dict[str, Any] = {"session_id": sid, "modified_at": mtime}
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            meta["simulation_complete"] = bool(data.get("simulation_complete"))
            meta["current_module"] = data.get("current_module")
            meta["current_timestep"] = data.get("current_timestep")
            curr = data.get("curriculum") or {}
            if isinstance(curr, dict):
                meta["title"] = curr.get("title")
        except (OSError, json.JSONDecodeError):
            pass
        out.append(meta)
    return out
