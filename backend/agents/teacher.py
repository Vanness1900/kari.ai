"""Teacher agent — expands module metadata into student-facing Markdown via OpenAI."""

from __future__ import annotations

import logging

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from orchestrator.state import ModuleConfig
from settings import Settings

logger = logging.getLogger(__name__)

# Teacher is fixed to this model (no Gemini / no alternate teacher models).
TEACHER_MODEL = "gpt-5.5"

_TIMESTEP_PHASE: dict[int, str] = {
    1: "DELIVER",
    2: "QNA",
    3: "EXERCISE",
    4: "ASSESS",
    5: "UPDATE",
}

# What the simulation expects at each phase (distinct prompts → distinct lesson text).
_PHASE_DIRECTIVE: dict[int, str] = {
    1: (
        "Phase DELIVER — First exposure. Include: Learning goals (bullets), Core ideas, "
        "one short Worked intuition, Common pitfalls. Full but concise."
    ),
    2: (
        "Phase QNA — Do NOT repeat the full lecture. Write clarifications only: likely student "
        "questions, short answers, and edge cases. Stay anchored to the module summary and "
        "any DELIVER excerpt below."
    ),
    3: (
        "Phase EXERCISE — Give 2–4 practice tasks for this module (scaffolded). "
        "Include brief hints only where needed. Stay anchored to the DELIVER excerpt below."
    ),
    4: (
        "Phase ASSESS — Short self-check: 3–5 questions or prompts; you may add one-line "
        "criteria for a correct answer. No long solutions. Align with the module and DELIVER excerpt."
    ),
    5: (
        "Phase UPDATE — One tight recap paragraph, one line on how this module connects forward, "
        "and optional bullet list of ‘take away’ facts. No full re-teach of the whole lesson."
    ),
}

_TEACHER_SYSTEM = (
    "You are an expert instructor. Write in GitHub-flavored Markdown for college-level learners. "
    "Follow the phase directive exactly. Stay within the module scope; do not invent prerequisites. "
    "When a DELIVER excerpt is provided, remain consistent with it."
)


def _timestep_messages(
    module: ModuleConfig,
    timestep: int,
    *,
    deliver_lesson: str | None,
) -> list[BaseMessage]:
    if timestep not in _TIMESTEP_PHASE:
        raise ValueError(f"timestep must be 1–5, got {timestep}")
    phase = _TIMESTEP_PHASE[timestep]
    directive = _PHASE_DIRECTIVE[timestep]

    deliver_block = ""
    if deliver_lesson and timestep > 1:
        deliver_block = (
            "\n\n---\nDELIVER excerpt from the same module (stay consistent):\n\n"
            f"{deliver_lesson.strip()}\n\n---\n"
        )

    human = HumanMessage(
        content=(
            f"**Phase:** {phase} (timestep {timestep}/5)\n\n"
            f"**Directive:** {directive}\n\n"
            f"Module id: `{module['id']}`\n"
            f"Title: {module['title']}\n"
            f"Target Bloom level (1–6): {module['blooms_level']}\n"
            f"Author summary:\n{module['summary']}\n"
            f"{deliver_block}\n"
            "Write the lesson body for this phase only (Markdown only, no YAML front matter)."
        )
    )
    return [SystemMessage(content=_TEACHER_SYSTEM), human]


def generate_timestep_markdown(
    module: ModuleConfig,
    timestep: int,
    *,
    settings: Settings,
    deliver_lesson: str | None = None,
) -> str:
    """One lesson body for this module phase (``gpt-5.5``).

    For timesteps 2–5, pass ``deliver_lesson`` (the generated DELIVER body for this module)
    so later phases stay aligned with the first pass.

    Requires ``OPENAI_API_KEY``; otherwise returns a deterministic stub.
    """
    if timestep not in _TIMESTEP_PHASE:
        raise ValueError(f"timestep must be 1–5, got {timestep}")

    if not settings.openai_api_key:
        return _stub_timestep_markdown(module, timestep)

    if timestep > 1 and not deliver_lesson:
        logger.warning(
            "Teacher timestep %s without deliver_lesson — phases may drift vs DELIVER.", timestep
        )

    messages = _timestep_messages(module, timestep, deliver_lesson=deliver_lesson)
    try:
        llm = ChatOpenAI(
            model=TEACHER_MODEL,
            api_key=settings.openai_api_key,
            temperature=0.4,
        )
        out = llm.invoke(messages)
        text = (out.content or "").strip()
        if not text:
            return _stub_timestep_markdown(module, timestep)
        return text
    except Exception:
        logger.exception("Teacher LLM failed; falling back to stub module text.")
        return _stub_timestep_markdown(module, timestep)


def generate_module_markdown(module: ModuleConfig, *, settings: Settings) -> str:
    """Deprecated convenience: same as timestep 1 DELIVER only."""
    return generate_timestep_markdown(module, 1, settings=settings, deliver_lesson=None)


def current_lesson_for_timestep(module_body: str, timestep: int) -> str:
    """Prefix line for `current_lesson` (body is already phase-specific)."""
    phase = _TIMESTEP_PHASE[timestep]
    return f"[{phase} | timestep {timestep}/5]\n\n{module_body}"


def _stub_timestep_markdown(module: ModuleConfig, timestep: int) -> str:
    phase = _TIMESTEP_PHASE[timestep]
    return (
        f"## [{phase}] {module['title']}\n\n"
        f"_Bloom level_: {module['blooms_level']}\n\n"
        f"{module['summary']}\n\n"
        f"(Stub phase `{phase}` for module `{module['id']}` — set OPENAI_API_KEY; model `{TEACHER_MODEL}`.)"
    )
