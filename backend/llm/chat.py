from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from settings import get_settings

Provider = Literal["openai", "gemini"]


def _provider_for_model(model: str) -> Provider:
    m = (model or "").lower()
    if "gemini" in m:
        return "gemini"
    return "openai"


def _get_chat_model(model: str):
    settings = get_settings()
    provider = _provider_for_model(model)

    if provider == "gemini":
        # Lazy import so OpenAI-only setups still work.
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set, but a Gemini model was requested."
            )
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=0.4,
        )

    # OpenAI
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set, but an OpenAI model was requested.")
    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key,
        temperature=0.4,
    )


def choose_model(preferred: str, *, fallback: str) -> str:
    """
    If preferred requires a missing API key, use fallback.
    """
    settings = get_settings()
    provider = _provider_for_model(preferred)
    if provider == "gemini" and not settings.google_api_key:
        return fallback
    if provider == "openai" and not settings.openai_api_key:
        return fallback
    return preferred


def llm_text(*, model: str, system: str, user: str) -> str:
    llm = _get_chat_model(model)
    # Avoid hanging forever on misconfigured provider/network.
    if hasattr(llm, "with_config"):
        llm = llm.with_config({"timeout": 30})
    res = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return str(getattr(res, "content", res))


def llm_json(*, model: str, system: str, user: str, max_retries: int = 2) -> dict[str, Any]:
    """
    Ask model to return strict JSON and parse it.
    Retries with a repair prompt if parsing fails.
    """
    llm = _get_chat_model(model)
    if hasattr(llm, "with_config"):
        llm = llm.with_config({"timeout": 30})

    base_system = system.strip() + "\n\nReturn ONLY valid JSON. No markdown, no code fences."
    last_text: str | None = None

    for attempt in range(max_retries + 1):
        if attempt == 0:
            messages = [SystemMessage(content=base_system), HumanMessage(content=user)]
        else:
            messages = [
                SystemMessage(content=base_system),
                HumanMessage(
                    content=(
                        "Your previous output was not valid JSON. "
                        "Return ONLY corrected JSON.\n\n"
                        f"Previous output:\n{last_text}"
                    )
                ),
            ]
        res = llm.invoke(messages)
        text = str(getattr(res, "content", res)).strip()
        last_text = text
        try:
            return json.loads(text)
        except Exception:
            continue

    raise ValueError(f"Model did not return valid JSON after retries. Last output: {last_text}")

