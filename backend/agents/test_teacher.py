"""Exercise the teacher agent against the sample curriculum.

Run from ``backend/`` (so ``.env`` / ``.env.local`` load):

    python agents/test_teacher.py

``--stub`` avoids the network and prints stub Markdown only.

``--module`` limits to a single module index (0-based).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ``agents``, ``orchestrator``, … are siblings under ``backend/``; this file lives in ``backend/agents/``.
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from agents.teacher import TEACHER_MODEL, current_lesson_for_timestep, generate_timestep_markdown
from orchestrator.state import blank_classroom_state
from settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Print teacher output per module and per timestep shell.")
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Force stub path (no OPENAI_API_KEY / no API calls).",
    )
    parser.add_argument(
        "--module",
        type=int,
        default=None,
        metavar="INDEX",
        help="Only this module index (0-based). Default: all modules.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.stub:
        settings = settings.model_copy(update={"openai_api_key": None})

    state = blank_classroom_state("test_teacher")
    modules = state["curriculum"]["modules"]

    if not args.stub and not settings.openai_api_key:
        print(
            "OPENAI_API_KEY is not set — use --stub or add a key to .env / .env.local.",
            file=sys.stderr,
        )
        return 1

    print(f"Teacher model (fixed): {TEACHER_MODEL}\n")

    indices = range(len(modules))
    if args.module is not None:
        if args.module < 0 or args.module >= len(modules):
            print(f"Module index {args.module} out of range (0–{len(modules) - 1}).", file=sys.stderr)
            return 1
        indices = [args.module]

    for mi in indices:
        mod = modules[mi]
        print("=" * 72)
        print(f"MODULE [{mi}]  id={mod['id']!r}  title={mod['title']!r}")
        print("=" * 72)

        # Same sequencing as orchestrator ``teacher_step``: DELIVER first, then pass its
        # body into timesteps 2–5 so QNA/EXERCISE/… stay aligned.
        deliver_snapshot: str | None = None
        for t in range(1, 6):
            body = generate_timestep_markdown(
                mod,
                t,
                settings=settings,
                deliver_lesson=deliver_snapshot if t > 1 else None,
            )
            if t == 1:
                deliver_snapshot = body

            print(f"\n--- Timestep {t} (phase-specific body → current_lesson wrapper)\n")
            lesson = current_lesson_for_timestep(body, t)
            print(lesson[:900] + ("…\n" if len(lesson) > 900 else "\n"))
            if len(lesson) > 900:
                print(f"(truncated; full length {len(lesson)} chars)\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
