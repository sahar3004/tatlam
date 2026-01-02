"""
tatlam/settings.py - Unified Configuration with Pydantic Validation

This module is the SINGLE SOURCE OF TRUTH for all configuration.
It replaces both config.py and config_trinity.py.

Features:
- Environment variable loading with validation
- Type safety via Pydantic
- Fail-fast on missing required API keys (configurable)
- Sensible defaults for development
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ThreatLevel(str, Enum):
    """Valid threat levels for scenarios."""

    LOW = "נמוכה"
    MEDIUM = "בינונית"
    HIGH = "גבוהה"
    VERY_HIGH = "גבוהה מאוד"


class Complexity(str, Enum):
    """Valid complexity levels for scenarios."""

    LOW = "נמוכה"
    MEDIUM = "בינונית"
    HIGH = "גבוהה"


class Likelihood(str, Enum):
    """Valid likelihood levels for scenarios."""

    LOW = "נמוכה"
    MEDIUM = "בינונית"
    HIGH = "גבוהה"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Boolean flags accept: 1, true, yes (case-insensitive) for True.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==== Base Paths ====
    # BASE_DIR is computed, not from env
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    @property
    def GOLD_DIR(self) -> Path:
        """Directory containing gold standard markdown examples."""
        return self.BASE_DIR / "gold_md"

    # ==== Database Configuration ====
    DB_PATH: str = Field(default="")
    TABLE_NAME: str = Field(default="scenarios")
    EMB_TABLE: str = Field(default="title_embeddings")

    @model_validator(mode="after")
    def set_default_db_path(self) -> Settings:
        """Set default DB_PATH relative to BASE_DIR if not provided."""
        if not self.DB_PATH:
            self.DB_PATH = str(self.BASE_DIR / "db" / "tatlam.db")
        # Ensure DB directory exists
        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        return self

    # ==== Scenario Filtering ====
    REQUIRE_APPROVED_ONLY: bool = Field(default=False)

    # ==== Trinity Architecture: Writer (Claude/Anthropic) ====
    WRITER_MODEL_PROVIDER: Literal["anthropic"] = "anthropic"
    WRITER_MODEL_NAME: str = Field(default="claude-sonnet-4-5-20250929")
    ANTHROPIC_API_KEY: str | None = Field(default=None)

    # ==== Trinity Architecture: Judge (Claude Opus for deep critique) ====
    JUDGE_MODEL_PROVIDER: Literal["anthropic"] = "anthropic"
    JUDGE_MODEL_NAME: str = Field(default="claude-opus-4-5-20251101")

    # ==== Trinity Architecture: Clerk (Gemini Flash for JSON formatting) ====
    CLERK_MODEL_PROVIDER: Literal["google"] = "google"
    CLERK_MODEL_NAME: str = Field(default="gemini-3-flash-preview")
    GOOGLE_API_KEY: str | None = Field(default=None)

    # ==== Trinity Architecture: Simulator (Gemini Flash for chat) ====
    SIMULATOR_MODEL_PROVIDER: Literal["google"] = "google"
    SIMULATOR_MODEL_NAME: str = Field(default="gemini-3-flash-preview")

    # ==== Trinity Architecture: Scout (Local Qwen for idea generation) ====
    LOCAL_MODEL_NAME: str = Field(default="qwen2.5-coder-32b-instruct")
    LOCAL_BASE_URL: str = Field(default="http://127.0.0.1:8080/v1")
    LOCAL_API_KEY: str = Field(default="sk-no-key-required")

    # ==== OpenAI Cloud (for batch processing / embeddings) ====
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_API_KEY: str | None = Field(default=None)

    # ==== Model Names (Legacy batch processing) ====
    GEN_MODEL: str = Field(default="gpt-4o")
    VALIDATOR_MODEL: str = Field(default="gpt-4o-mini")
    CHECKER_MODEL: str = Field(default="gpt-4o-mini")
    EMBED_MODEL: str = Field(default="text-embedding-3-small")

    # ==== Processing Parameters ====
    BATCH_COUNT: int = Field(default=5, ge=1, le=50)
    SIM_THRESHOLD: float = Field(default=0.88, ge=0.0, le=1.0)
    CANDIDATE_COUNT: int = Field(default=8, ge=1, le=50)
    KEEP_TOP_K: int = Field(default=5, ge=1, le=50)
    DIVERSITY_MAX_SIM: float = Field(default=0.92, ge=0.0, le=1.0)
    CHAT_RETRIES: int = Field(default=3, ge=1, le=10)

    # ==== Gold Examples Configuration ====
    GOLD_SCOPE: str = Field(default="category")
    GOLD_DB_LIMIT: int = Field(default=30, ge=1)
    GOLD_MAX_CHARS: int = Field(default=6000, ge=100)
    GOLD_EXAMPLES: int = Field(default=4, ge=0)
    GOLD_FS_DIR: str = Field(default="gold_md")

    # ==== Application Configuration ====
    PAGE_TITLE: str = Field(default="Tatlam Trinity System")
    FLASK_SECRET_KEY: str | None = Field(default=None)

    # ==== Validation Mode ====
    # When True, missing API keys raise ConfigurationError at startup
    STRICT_API_VALIDATION: bool = Field(default=False)

    @field_validator("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for API keys."""
        if v is not None and isinstance(v, str) and not v.strip():
            return None
        return v

    # ==== Convenience Properties ====

    @property
    def LOCAL_MODEL(self) -> str:
        """Alias for LOCAL_MODEL_NAME (backward compatibility)."""
        return self.LOCAL_MODEL_NAME

    def has_writer(self) -> bool:
        """Check if Writer (Anthropic) is configured."""
        return self.ANTHROPIC_API_KEY is not None

    def has_judge(self) -> bool:
        """Check if Judge (Google) is configured."""
        return self.GOOGLE_API_KEY is not None

    def has_openai(self) -> bool:
        """Check if OpenAI cloud is configured."""
        return self.OPENAI_API_KEY is not None


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses LRU cache to ensure settings are only loaded once.
    Call get_settings.cache_clear() to reload settings (useful in tests).

    Returns:
        Settings: Validated application settings

    Raises:
        ConfigurationError: If STRICT_API_VALIDATION is True and required keys are missing
    """
    settings = Settings()

    if settings.STRICT_API_VALIDATION:
        missing = []
        if not settings.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not settings.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if missing:
            raise ConfigurationError(
                f"Missing required API keys: {', '.join(missing)}. "
                "Set STRICT_API_VALIDATION=false to allow missing keys."
            )

    return settings


# ==== Module-Level Exports for Backward Compatibility ====
# These allow: from tatlam.settings import DB_PATH, TABLE_NAME
# Instead of: from tatlam.settings import get_settings; settings = get_settings(); settings.DB_PATH


def __getattr__(name: str) -> Any:
    """
    Module-level attribute access for backward compatibility.

    Allows importing constants directly:
        from tatlam.settings import DB_PATH, ANTHROPIC_API_KEY

    This is a convenience layer; prefer using get_settings() for new code.
    """
    settings = get_settings()

    # Handle special properties
    if name == "GOLD_DIR":
        return settings.GOLD_DIR
    if name == "LOCAL_MODEL":
        return settings.LOCAL_MODEL

    # Handle regular attributes
    if hasattr(settings, name):
        return getattr(settings, name)

    raise AttributeError(f"module 'tatlam.settings' has no attribute '{name}'")


# Explicit exports for IDE support and static analysis
__all__ = [
    # Classes
    "Settings",
    "ConfigurationError",
    "ThreatLevel",
    "Complexity",
    "Likelihood",
    # Functions
    "get_settings",
    # Constants (accessed via __getattr__)
    "BASE_DIR",
    "GOLD_DIR",
    "DB_PATH",
    "TABLE_NAME",
    "EMB_TABLE",
    "REQUIRE_APPROVED_ONLY",
    "WRITER_MODEL_PROVIDER",
    "WRITER_MODEL_NAME",
    "ANTHROPIC_API_KEY",
    "JUDGE_MODEL_PROVIDER",
    "JUDGE_MODEL_NAME",
    "GOOGLE_API_KEY",
    "LOCAL_MODEL_NAME",
    "LOCAL_MODEL",
    "LOCAL_BASE_URL",
    "LOCAL_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "GEN_MODEL",
    "VALIDATOR_MODEL",
    "CHECKER_MODEL",
    "EMBED_MODEL",
    "BATCH_COUNT",
    "SIM_THRESHOLD",
    "CANDIDATE_COUNT",
    "KEEP_TOP_K",
    "DIVERSITY_MAX_SIM",
    "CHAT_RETRIES",
    "GOLD_SCOPE",
    "GOLD_DB_LIMIT",
    "GOLD_MAX_CHARS",
    "GOLD_EXAMPLES",
    "GOLD_FS_DIR",
    "PAGE_TITLE",
    "FLASK_SECRET_KEY",
]
