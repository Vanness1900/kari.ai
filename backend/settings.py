"""Application settings loaded from environment (.env optional)."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Env vars documented in `.env.example` and CLAUDE.md."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")

    chroma_db_path: Path = Field(
        default=_BACKEND_DIR / "chroma_db",
        alias="CHROMA_DB_PATH",
    )
    uploads_path: Path = Field(
        default=_BACKEND_DIR / "uploads",
        alias="UPLOADS_PATH",
    )
    sessions_path: Path = Field(
        default=_BACKEND_DIR / "sessions",
        alias="SESSIONS_PATH",
    )

    default_student_model: str = Field(
        default="gemini-2.0-flash",
        alias="DEFAULT_STUDENT_MODEL",
    )
    default_reasoning_model: str = Field(
        default="gpt-4o",
        alias="DEFAULT_REASONING_MODEL",
    )

    use_llm_assessor: bool = Field(
        default=True,
        alias="USE_LLM_ASSESSOR",
        description="If True and GOOGLE_API_KEY is set, assessor uses Gemini per student.",
    )

    use_llm_insight: bool = Field(
        default=True,
        alias="USE_LLM_INSIGHT",
        description="If True and an LLM key is set, insight uses OpenAI (or Gemini fallback).",
    )

    enable_visual_report: bool = Field(
        default=False,
        alias="ENABLE_VISUAL_REPORT",
    )

    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    def ensure_data_dirs(self) -> None:
        self.uploads_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
