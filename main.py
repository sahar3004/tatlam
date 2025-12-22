import streamlit as st
import asyncio
import sys
import os
import requests
from loguru import logger

# Fix Imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Try Imports
try:
    from tatlam.core.llm_factory import create_simulator_client, create_writer_client
    from tatlam.core.brain import TrinityBrain
    from tatlam.infra.db import init_db
    from tatlam.settings import get_settings
except ImportError as e:
    st.error(f"Critical Error: Could not load system core. {e}")
    st.stop()

# Get settings
settings = get_settings()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="מערכת תתל״מ - מרכז שליטה",
    page_icon="🇮🇱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- RTL & STYLING ---
def apply_rtl_style():
    st.markdown("""
        <style>
        .stApp { direction: rtl; text-align: right; }
        h1, h2, h3, h4, h5, h6, p, div, span { text-align: right; font-family: 'Segoe UI', Tahoma, sans-serif; }
        .stSidebar { text-align: right; direction: rtl; }
        [data-testid="stMetricValue"] { direction: ltr; text-align: right; }
        .stTextInput input, .stTextArea textarea { direction: rtl; text-align: right; }
        /* JSON LTR fix */
        .stJson { direction: ltr; text-align: left; }
        </style>
    """, unsafe_allow_html=True)

apply_rtl_style()

# --- SYSTEM HEALTH CHECK ---
@st.cache_resource
def system_check():
    status = {"db": False, "local": False}
    try:
        init_db()
        status["db"] = True
    except Exception:
        pass

    try:
        r = requests.get("http://localhost:8080/health", timeout=0.5)
        if r.status_code == 200:
            status["local"] = True
    except Exception:
        pass
    return status

status = system_check()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎯 ניווט מערכת")

    if status["db"]:
        st.success("✅ בסיס נתונים (מחובר)")
    else:
        st.error("❌ בסיס נתונים (תקלה)")

    if status["local"]:
        st.success("✅ מוח מקומי (Qwen 32B)")
    else:
        st.error("❌ מוח מקומי (מנותק)")
        st.warning("יש להריץ בטרמינל:\n`./run_engine.sh`")

    st.markdown("---")
    st.markdown("### הגדרות ייצור")
    mode = st.radio(
        "מצב עבודה:",
        ["🚀 טיוטה מהירה (מקומי)", "✨ עיבוד מלא (ענן + מקומי)"],
        index=1
    )

# --- MAIN LOGIC (Hybrid Engine) ---
st.title("🛡️ מחולל תרחישים מבצעי - דור 2025")
st.caption("מנוע היברידי: M4 Pro Local Engine + Cloud Refinery")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("פרמטרים")
    category = st.selectbox("קטגוריית אירוע",
                          ["חפץ חשוד", "פח״ע", "סייבר והשפעה", "רעידת אדמה", "חדירת מחבלים", "אירוע רב-זירתי"])
    threat_level = st.select_slider("רמת איום", options=["שגרה", "חשד נמוך", "גבוה", "קריטי (חירום)"])
    location = st.text_input("מיקום", "קניון עזריאלי, תל אביב")

with col2:
    st.subheader("מודיעין ורקע")
    base_context = st.text_area("תיאור חופשי",
                                value="התקבל דיווח על דמות חשודה המצלמת את עמדות המאבטחים...",
                                height=150)


class HybridBrain:
    """Hybrid Brain: Local Drafter + Cloud Refiner."""

    def __init__(self, local_client=None, refiner_client=None):
        self.local_client = local_client
        self.refiner_client = refiner_client
        self._settings = get_settings()

    async def generate_draft(self, category: str, threat_level: str, context: str) -> dict:
        """Generate initial draft using local LLM."""
        if not self.local_client:
            raise RuntimeError("Local client not initialized")

        prompt = f"""אתה מומחה אבטחה ישראלי. צור תרחיש אימון מבצעי.

קטגוריה: {category}
רמת איום: {threat_level}
הקשר: {context}

החזר JSON עם השדות הבאים:
- title: כותרת התרחיש
- background: רקע מבצעי
- steps: רשימת שלבי האירוע (מערך)
- required_response: תגובה נדרשת (מערך)
- threat_level: רמת האיום

החזר JSON בלבד, ללא טקסט נוסף."""

        response = self.local_client.chat.completions.create(
            model=self._settings.LOCAL_MODEL_NAME,
            messages=[
                {"role": "system", "content": "אתה מומחה אבטחה מבצעית. החזר JSON בלבד."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        import json
        content = response.choices[0].message.content
        return json.loads(content)

    async def refine_scenario(self, draft: dict) -> dict:
        """Refine draft using cloud LLM (Claude)."""
        if not self.refiner_client:
            # No cloud - return draft as-is
            return draft

        import json

        prompt = f"""בצע ליטוש דוקטרינרי לתרחיש האימון הבא.
שפר את הניסוח, הוסף פרטים מבצעיים, וודא התאמה לסטנדרטים מקצועיים.

תרחיש מקורי:
{json.dumps(draft, ensure_ascii=False, indent=2)}

החזר JSON משופר עם אותם שדות."""

        response = self.refiner_client.messages.create(
            model=self._settings.WRITER_MODEL_NAME,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        content = response.content[0].text

        # Try to parse JSON from response
        try:
            # Find JSON in response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        # If parsing fails, return original draft with refinement note
        draft['refinement_note'] = content
        return draft


async def execute_mission():
    placeholder = st.empty()
    logs = st.status("🔄 מערכת בפעולה...", expanded=True)

    try:
        # 1. Local Drafter
        logs.write("🧠 מפעיל מנוע מקומי (Drafter)...")
        local_client = create_simulator_client()

        # 2. Cloud Refiner (optional)
        cloud_client = None
        if "עיבוד מלא" in mode:
            try:
                logs.write("☁️ יוצר קשר עם הענן (Refiner)...")
                cloud_client = create_writer_client()
            except Exception as e:
                logs.warning(f"אין חיבור לענן: {e}. ממשיך מקומי.")

        brain = HybridBrain(local_client=local_client, refiner_client=cloud_client)

        # 3. Execution
        logs.write("📝 מייצר שלד תרחיש...")
        draft = await brain.generate_draft(
            category=category,
            threat_level=threat_level,
            context=f"מיקום: {location}. {base_context}"
        )

        if cloud_client:
            logs.write("✨ מבצע ליטוש דוקטרינרי...")
            final = await brain.refine_scenario(draft)
            logs.update(label="✅ סיום מוצלח!", state="complete", expanded=False)
            return final
        else:
            logs.update(label="✅ טיוטה מוכנה", state="complete", expanded=False)
            return draft

    except Exception as e:
        logs.update(label="❌ שגיאה", state="error")
        st.error(f"Error: {str(e)}")
        logger.exception(f"Mission execution failed: {e}")
        return None


if st.button("צור תרחיש כעת ⚡", type="primary", use_container_width=True):
    if not status["local"]:
        st.error("המודל המקומי כבוי. אנא הפעל את השרת עם ./run_engine.sh")
    else:
        result = asyncio.run(execute_mission())
        if result:
            st.divider()
            t1, t2 = st.tabs(["תצוגה מבצעית", "JSON"])
            with t1:
                st.subheader(result.get('title', 'ללא כותרת'))
                st.info(result.get('background', ''))

                steps = result.get('steps', [])
                if steps:
                    st.markdown("**שלבי האירוע:**")
                    for i, step in enumerate(steps, 1):
                        if isinstance(step, dict):
                            st.text(f"{i}. {step.get('time', '')} - {step.get('description', step)}")
                        else:
                            st.text(f"{i}. {step}")

                response = result.get('required_response', [])
                if response:
                    st.markdown("**תגובה נדרשת:**")
                    for item in response:
                        st.text(f"• {item}")

            with t2:
                st.json(result)
