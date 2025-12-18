import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
GOLD_DIR = BASE_DIR / "gold_md"

# Database Configuration (from existing config.py)
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "db" / "tatlam.db"))
TABLE_NAME = os.getenv("TABLE_NAME", "scenarios")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# 1. The Writer (Claude)
WRITER_MODEL_PROVIDER = "anthropic"
WRITER_MODEL_NAME = os.getenv("WRITER_MODEL_NAME", "claude-3-7-sonnet-20250219")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 2. The Judge (Gemini)
JUDGE_MODEL_PROVIDER = "google"
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "gemini-2.0-pro-exp-0205")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 3. The Simulator (Local Llama)
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "llama-4-70b-instruct")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "sk-no-key-required")

# App Config
PAGE_TITLE = "Tatlam Trinity System"
