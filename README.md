# tatlam (ייצור תטל"מים)

## התקנה מהירה
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `pip install -r requirements-dev.txt` (לבדיקות ו-QA)
4. `cp .env.template .env` ואז עריכה של ערכי API/DB/לוגים
5. `export TMPDIR=~/tmp && mkdir -p ~/tmp` כדי למנוע אזהרות Python במק מקומי
6. אפשר גם להשתמש בפקודות Make: `make dev`

## הרצה
- לחיצה כפולה ב‑Finder: `start_flask.command` (מקים venv, מתקין תלויות במידת הצורך, ומעלה Flask)
- Flask דרך CLI: `./scripts/start_flask.sh` או `make run`
- מודל מקומי (llama.cpp): `./scripts/start_local_llm.sh` או לחיצה כפולה `start_local_llm.command`
- באצ' יצירת תטל"מים: `python run_batch.py --category "כבודה עזובה / חפץ חשוד / מטען"`
- ייצוא JSON: `python export_json.py --category "כבודה עזובה / חפץ חשוד / מטען" --out out.json`
- רנדר Markdown: `python render_cards.py --category "כבודה עזובה / חפץ חשוד / מטען" --out ./cards/`

## QA ובדיקות
- `make qa-baseline` — מריץ בדיקות/כיסויים + smoke ומפיק ארטיפקטים תחת `artifacts/baseline/<ts>`
- `make qa-changed` — מריץ linters/types/security/tests ושומר לוגים תחת `artifacts/runs/<ts>`
- ידנית: `pytest`, `ruff check .`, `black --check .`, `mypy --strict .`, `bandit -r .`, `pip-audit`
- כיסוי יעד ≥85% (כרגע נמוך יותר; ראו דוח סופי והצעת תכנית להעלאה)

## סימולציות
- ריצה דטרמיניסטית: `python -m tatlam.simulate artifacts/runs/<ts>/payload.json --out artifacts/runs/<ts>/results.json`

## תצורה
- כל משתני הסביבה מתועדים ב-`.env.template`
- קונפיג לוגים אחיד: `tatlam.logging_setup.configure_logging`
