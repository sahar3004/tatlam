# config.py
"""
Tatlam – מרכז תצורה אחד לכל המערכת:
- מסדי נתונים וסקימות
- מודלים (ענן/לוקלי)
- לקוחות OpenAI תואמי API
- דגלים ותצורות עבור יצירה/ולידציה/אדמין
"""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

# ==== Utilities ====


def _getint(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _getfloat(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _getbool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ==== נתיבי בסיס ====
BASE_DIR = Path(__file__).resolve().parent
# אם לא הוגדר – נשמור בתוך ./db/tatlam.db
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "db" / "tatlam.db"))
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ==== שמות טבלאות ופרמטרים כלליים ====
TABLE_NAME: str = os.getenv("TABLE_NAME", "scenarios")
EMB_TABLE: str = os.getenv("EMB_TABLE", "title_embeddings")
BATCH_COUNT: int = _getint("BATCH_COUNT", 5)
SIM_THRESHOLD: float = _getfloat("SIM_THRESHOLD", 0.88)

# ==== מודלים (ענן) ====
# GEN_MODEL – מודל היצירה המרכזי
GEN_MODEL: str = os.getenv("GEN_MODEL", "gpt-5")
# VALIDATOR/CHECKER – תיקוף ושיפוט
VALIDATOR_MODEL: str = os.getenv("VALIDATOR_MODEL", "gpt-5-mini")
CHECKER_MODEL: str = os.getenv("CHECKER_MODEL", "gpt-5-mini")
# אמבדינגים
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# ==== מודל מקומי (OpenAI-compatible server כדוגמת llama.cpp) ====
# דוגמה ל-.env:
# LOCAL_BASE_URL=http://127.0.0.1:8080/v1
# LOCAL_API_KEY=sk-local-dummy
# LOCAL_MODEL=gpt-oss-20b-mxfp4
LOCAL_BASE_URL: str = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_API_KEY: str = os.getenv("LOCAL_API_KEY", "sk-local")
LOCAL_MODEL: str = os.getenv("LOCAL_MODEL", "gpt-oss-20b-mxfp4")

# ==== OpenAI – ענן ====
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")  # שים ב-.env

# ==== דגלים ותצורות ל-Run/Gold ====
# שליפת דוגמאות GOLD להשראה (scope=all/category/none)
GOLD_SCOPE: str = os.getenv("GOLD_SCOPE", "category")
GOLD_DB_LIMIT: int = _getint("GOLD_DB_LIMIT", 30)
GOLD_MAX_CHARS: int = _getint("GOLD_MAX_CHARS", 6000)
GOLD_EXAMPLES: int = _getint("GOLD_EXAMPLES", 4)
# ייצור מועמדים ושמירת המובחרים
CANDIDATE_COUNT: int = _getint("CANDIDATE_COUNT", 8)
KEEP_TOP_K: int = _getint("KEEP_TOP_K", 5)
DIVERSITY_MAX_SIM: float = _getfloat("DIVERSITY_MAX_SIM", 0.92)
CHAT_RETRIES: int = _getint("CHAT_RETRIES", 3)
REQUIRE_APPROVED_ONLY: bool = _getbool("REQUIRE_APPROVED_ONLY", False)

# ==== Flask/App ====
# נקרא ב-app.py; לא נחשוף בלוגים
FLASK_SECRET_KEY: str | None = os.getenv("FLASK_SECRET_KEY")


# ==== לקוחות OpenAI ====


def client_local() -> OpenAI:
    """
    מחזיר לקוח OpenAI שמדבר עם שרת מקומי תואם-OpenAI (למשל llama.cpp server).
    השרת מספק נקודות קצה בסגנון /v1/chat/completions ו-/v1/embeddings.
    """
    return OpenAI(base_url=LOCAL_BASE_URL, api_key=LOCAL_API_KEY)


def client_cloud() -> OpenAI:
    """
    מחזיר לקוח OpenAI הרשמי לענן. דורש OPENAI_API_KEY בסביבה.
    """
    return OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)


# ==== עזר לאימות סביבת הרצה (לוג בלבד; ללא דליפת מפתחות) ====


def describe_effective_config() -> dict[str, object]:
    return {
        "DB_PATH": DB_PATH,
        "TABLE_NAME": TABLE_NAME,
        "EMB_TABLE": EMB_TABLE,
        "BATCH_COUNT": BATCH_COUNT,
        "SIM_THRESHOLD": SIM_THRESHOLD,
        "GEN_MODEL": GEN_MODEL,
        "VALIDATOR_MODEL": VALIDATOR_MODEL,
        "CHECKER_MODEL": CHECKER_MODEL,
        "EMBED_MODEL": EMBED_MODEL,
        "LOCAL_BASE_URL": LOCAL_BASE_URL,
        "LOCAL_MODEL": LOCAL_MODEL,
        "OPENAI_BASE_URL": OPENAI_BASE_URL,
        "OPENAI_API_KEY_SET": bool(OPENAI_API_KEY),
        "FLASK_SECRET_KEY_SET": bool(FLASK_SECRET_KEY),
        "GOLD_SCOPE": GOLD_SCOPE,
        "GOLD_DB_LIMIT": GOLD_DB_LIMIT,
        "GOLD_MAX_CHARS": GOLD_MAX_CHARS,
        "GOLD_EXAMPLES": GOLD_EXAMPLES,
        "CANDIDATE_COUNT": CANDIDATE_COUNT,
        "KEEP_TOP_K": KEEP_TOP_K,
        "DIVERSITY_MAX_SIM": DIVERSITY_MAX_SIM,
        "CHAT_RETRIES": CHAT_RETRIES,
        "REQUIRE_APPROVED_ONLY": REQUIRE_APPROVED_ONLY,
    }


__all__ = [
    # DB & schema
    "DB_PATH",
    "TABLE_NAME",
    "EMB_TABLE",
    # generation knobs
    "BATCH_COUNT",
    "SIM_THRESHOLD",
    "GEN_MODEL",
    "VALIDATOR_MODEL",
    "CHECKER_MODEL",
    "EMBED_MODEL",
    # local/cloud endpoints
    "LOCAL_BASE_URL",
    "LOCAL_API_KEY",
    "LOCAL_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    # run/gold flags
    "GOLD_SCOPE",
    "GOLD_DB_LIMIT",
    "GOLD_MAX_CHARS",
    "GOLD_EXAMPLES",
    "CANDIDATE_COUNT",
    "KEEP_TOP_K",
    "DIVERSITY_MAX_SIM",
    "CHAT_RETRIES",
    "REQUIRE_APPROVED_ONLY",
    # flask
    "FLASK_SECRET_KEY",
    # clients & helpers
    "client_local",
    "client_cloud",
    "describe_effective_config",
]
