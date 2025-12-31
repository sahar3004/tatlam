# tatlam (ייצור תטל"מים)

## Architecture Overview

### Database Layer (SQLAlchemy 2.0)
The project uses SQLAlchemy 2.0 ORM with type-annotated models for robust database operations:

- **WAL Mode**: SQLite Write-Ahead Logging enabled for better concurrent access
- **Connection Pooling**: Automatic connection management with pool_pre_ping
- **Indexed Queries**: Performance indexes on `category`, `threat_level`, `status`, `created_at`
- **Session Management**: Context-managed sessions with auto-commit/rollback

```python
from tatlam.infra.db import get_session
from tatlam.infra.models import Scenario

with get_session() as session:
    scenarios = session.scalars(select(Scenario)).all()
```

### Trinity Architecture
Three-model AI system for scenario generation:
- **Writer** (Claude/Anthropic): Creative scenario drafting
- **Judge** (Gemini/Google): Quality validation and scoring
- **Simulator** (Local/OpenAI-compatible): Testing and verification

### Async Processing (M4 Pro Optimized)
- Semaphore-controlled concurrency (default: 8 parallel tasks)
- Optimized for 48GB RAM with WAL mode database access
- `run_batch.py --async` for faster batch processing

## התקנה מהירה
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `pip install -r requirements-dev.txt` (לבדיקות ו-QA)
4. `cp .env.template .env` ואז עריכה של ערכי API/DB/לוגים
5. `export TMPDIR=~/tmp && mkdir -p ~/tmp` כדי למנוע אזהרות Python במק מקומי
6. אפשר גם להשתמש בפקודות Make: `make dev`

## הרצה
- ממשק משתמש (Streamlit): `./start_ui.sh`
- מודל מקומי (llama.cpp): `./scripts/start_local_llm.sh` או לחיצה כפולה `start_local_llm.command`
- באצ' יצירת תטל"מים: `python run_batch.py --category "כבודה עזובה / חפץ חשוד / מטען"`
- ייצוא JSON: `python export_json.py --category "כבודה עזובה / חפץ חשוד / מטען" --out out.json`
- רנדר Markdown: `python render_cards.py --category "כבודה עזובה / חפץ חשוד / מטען" --out ./cards/`

### CLI מותקנים (Console Scripts)
לאחר `pip install -e .` ניתן להשתמש בפקודות הבאות במקום `python <script>.py`:
- `tatlam-export-json --category "חפץ חשוד ומטען" --out out.json`
- `tatlam-render-cards --category "חפץ חשוד ומטען" --out ./cards/ [--limit 10]`
- `tatlam-sim [payload.json] --out artifacts/simulation_results.json`

הקבצים ברמת‑שורש נשארים כשכבת תאימות; מומלץ לעבור לפקודות לעיל.

## QA ובדיקות
- `make qa-baseline` — מריץ בדיקות/כיסויים + smoke ומפיק ארטיפקטים תחת `artifacts/baseline/<ts>`
- `make qa-changed` — מריץ linters/types/security/tests ושומר לוגים תחת `artifacts/runs/<ts>`
- ידנית: `pytest`, `ruff check .`, `black --check .`, `mypy --strict .`, `bandit -r .`, `pip-audit`
- כיסוי יעד ≥85% (כרגע נמוך יותר; ראו דוח סופי והצעת תכנית להעלאה)

## סימולציות
- ריצה דטרמיניסטית: `python -m tatlam.simulate artifacts/runs/<ts>/payload.json --out artifacts/runs/<ts>/results.json`

או באמצעות CLI: `tatlam-sim --out artifacts/simulation_results.json`

## שרת מקומי תואם‑OpenAI (llama.cpp)
הפרויקט תומך בהפעלת שרת מקומי תואם‑OpenAI עבור פיתוח ללא ענן.

צעדים מהירים (macOS/Homebrew):
- התקינו llama.cpp (מכיל את `llama-server`): `brew install llama.cpp`
- הורידו מודל GGUF מתאים (למשל Llama 3.1 instruct) ושמרו בנתיב מקומי.
- עדכנו ב־`.env` את:
  - `LOCAL_MODEL_PATH=/path/to/model.gguf`
  - אופציונלי: `LOCAL_HOST`, `LOCAL_PORT`, `LLM_THREADS`, `LLM_CONTEXT`, `LLAMA_BIN`
- הפעילו: `./start_local_llm.command` (או `scripts/start_local_llm.sh -m /path/to/model.gguf`)

הסקריפט מפעיל `llama-server` עם API‑Key מקומי (`LOCAL_API_KEY`, כברירת מחדל `sk-local`).
האפליקציה מתקשרת אליו דרך `LOCAL_BASE_URL` מה־`.env`.

## תצורה
- כל משתני הסביבה מתועדים ב-`.env.template`
- קונפיג לוגים אחיד: `tatlam.logging_setup.configure_logging`

## App Factory (ל‑WSGI/ASGI)
- ניתן לקבל מופע Flask ע"י: `from tatlam.web.factory import create_app; app = create_app()`
- זה מחזיר את `app` המוגדר ב-`app.py` תוך שימוש בטעינה דינמית.

## CI
- מאותו פרויקט מוגדר Workflow של GitHub Actions שמריץ: ruff, black, mypy (על `tatlam/`), bandit, pip‑audit, ו‑pytest.
- לוגים וארטיפקטים נשמרים תחת `artifacts/runs/<ts>/` בדומה להרצה מקומית של `make qa-changed`.
