"""Teacher agent — expands module metadata into student-facing Markdown."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from orchestrator.state import ModuleConfig
from settings import Settings

logger = logging.getLogger(__name__)

_TEACHER_SYSTEM = (
    "You are an expert instructor. Produce concise lesson content in GitHub-flavored "
    "Markdown for college-level learners. Use short sections: Learning goals (bullets), "
    "Core ideas, Worked intuition (one mini example), "
    "Common pitfalls. Stay within the module scope; do not invent prerequisites."
)


def generate_module_markdown(module: ModuleConfig, *, settings: Settings) -> str:
    """Expand curriculum module row into one lesson Markdown body.

    Uses Gemini when ``GOOGLE_API_KEY`` is configured; otherwise a deterministic stub
    so the simulation runs offline.
    """
    if not settings.google_api_key:
        return _stub_module_markdown(module)

    # Lazy import so imports succeed without Google deps in minimal environments.
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.default_teacher_model,
        google_api_key=settings.google_api_key,
        temperature=0.4,
    )
    human = HumanMessage(
        content=(
            f"Module id: `{module['id']}`\n"
            f"Title: {module['title']}\n"
            f"Target Bloom level (1–6): {module['blooms_level']}\n"
            f"Author summary:\n{module['summary']}\n\n"
            "Write the lesson body now (Markdown only, no YAML front matter)."
        )
    )
    try:
        out = llm.invoke(
            [SystemMessage(content=_TEACHER_SYSTEM), human],
        )
        text = (out.content or "").strip()
        if not text:
            return _stub_module_markdown(module)
        return text
    except Exception:
        logger.exception("Teacher LLM failed; falling back to stub module text.")
        return _stub_module_markdown(module)


def _stub_module_markdown(module: ModuleConfig) -> str:
    return (
        f"## {module['title']}\n\n"
        f"_Bloom level_: {module['blooms_level']}\n\n"
        f"{module['summary']}\n\n"
        f"(Stub generated content for module `{module['id']}` — set GOOGLE_API_KEY for live teacher.)"
    )
