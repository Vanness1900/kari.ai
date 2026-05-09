"""Exercise student agents against a sample lesson (canned or full teacher pipeline).

Run from ``backend/`` (loads ``.env`` / ``.env.local`` via ``settings``):

    python agents/test_students.py

``--stub`` — force deterministic student stub (no Gemini; no ``GOOGLE_API_KEY``).

By default the lesson text is **canned** so you only need Google for live student calls.
``--live-lesson`` generates phase-specific Markdown via the teacher (needs ``OPENAI_API_KEY``).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from agents.student import run_student_turn
from agents.teacher import current_lesson_for_timestep, generate_timestep_markdown
from orchestrator.state import StudentProfile, blank_classroom_state
from settings import get_settings

# Short fixed body when not using the teacher LLM (students still see phase prefixes).
CANNED_LESSON_BODY = """## Sample module (canned for student tests)

You are seeing placeholder lesson Markdown. Respond according to your profile and the knowledge gate.

- Concept A: described briefly.
- Pitfall: a common mistake learners make.
"""


def _print_turn(
    student: StudentProfile,
    label: str,
    out: dict,
) -> None:
    print(f"  {label}")
    print(f"    {json.dumps(out, indent=2, sort_keys=True).replace(chr(10), chr(10) + '    ')}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run student agents on each timestep with a shared current_lesson."
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Force student stub (no Gemini / ignore GOOGLE_API_KEY).",
    )
    parser.add_argument(
        "--live-lesson",
        action="store_true",
        help="Call the teacher (gpt-5.5) per timestep for lesson bodies; requires OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--module",
        type=int,
        default=0,
        metavar="INDEX",
        help="Curriculum module index (default: 0).",
    )
    parser.add_argument(
        "--student",
        type=int,
        default=None,
        metavar="INDEX",
        help="Only this student index. Default: all students in blank_classroom_state.",
    )
    parser.add_argument(
        "--timestep",
        type=int,
        default=None,
        metavar="N",
        help="Only this timestep 1–5. Default: all timesteps.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.stub:
        settings = settings.model_copy(update={"google_api_key": None})

    if not args.stub and not settings.google_api_key:
        print(
            "GOOGLE_API_KEY is not set — use --stub for deterministic students, "
            "or add a key to backend/.env.local.",
            file=sys.stderr,
        )
        return 1

    if args.live_lesson and not settings.openai_api_key:
        print(
            "OPENAI_API_KEY is not set — cannot use --live-lesson. "
            "Omit --live-lesson for canned lesson text, or add a key.",
            file=sys.stderr,
        )
        return 1

    state = blank_classroom_state("test_students")
    modules = state["curriculum"]["modules"]
    if args.module < 0 or args.module >= len(modules):
        print(f"Module index {args.module} out of range (0–{len(modules) - 1}).", file=sys.stderr)
        return 1

    mod = modules[args.module]
    students: list[StudentProfile] = state["students"]
    if args.student is not None:
        if args.student < 0 or args.student >= len(students):
            print(f"Student index {args.student} out of range (0–{len(students) - 1}).", file=sys.stderr)
            return 1
        students = [students[args.student]]

    timesteps = range(1, 6)
    if args.timestep is not None:
        if args.timestep < 1 or args.timestep > 5:
            print("timestep must be 1–5.", file=sys.stderr)
            return 1
        timesteps = [args.timestep]

    if args.stub:
        mode = "student: stub"
    else:
        mode = f"student: Gemini ({settings.default_student_model})"
    if args.live_lesson:
        mode += " | lesson: teacher gpt-5.5"
    else:
        mode += " | lesson: canned Markdown"
    print(f"{mode}\n")

    deliver_snapshot: str | None = None
    teacher_settings = get_settings()

    for t in timesteps:
        if args.live_lesson:
            body = generate_timestep_markdown(
                mod,
                t,
                settings=teacher_settings,
                deliver_lesson=deliver_snapshot if t > 1 else None,
            )
            if t == 1:
                deliver_snapshot = body
        else:
            body = CANNED_LESSON_BODY

        lesson = current_lesson_for_timestep(body, t)
        phase_line = lesson.split("\n", 1)[0]

        print("=" * 72)
        print(f"timestep={t}  module={mod['title']!r}  {phase_line}")
        print("=" * 72)

        all_students = state["students"]
        for stu_template in students:
            student = copy.deepcopy(stu_template)
            sid = student["id"]
            out = run_student_turn(
                student,
                current_lesson=lesson,
                timestep=t,
                module_title=mod["title"],
                settings=settings,
            )
            idx = all_students.index(stu_template)
            _print_turn(student, f"student[{idx}] {sid} ({student['name']})", out)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
