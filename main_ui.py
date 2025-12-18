import streamlit as st
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

# Logging setup
from tatlam.logging_setup import configure_logging
import logging

configure_logging()
logger = logging.getLogger(__name__)

# Trinity imports
from tatlam.core.brain import TrinityBrain
import config_trinity

# Persistence imports
from tatlam.infra.repo import insert_scenario
from tatlam.core.gold_md import parse_md_to_scenario


# Page Configuration
st.set_page_config(
    page_title=config_trinity.PAGE_TITLE,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# RTL STYLING & HEBREW UI
# ============================================================================

def apply_rtl_style():
    """Apply RTL styling for Hebrew UI."""
    st.markdown("""
        <style>
        /* Global RTL */
        .stApp { direction: rtl; text-align: right; }

        /* Headers alignment */
        h1, h2, h3, h4, h5, h6 { text-align: right; font-family: 'Segoe UI', Tahoma, sans-serif; }

        /* Metrics Styling */
        [data-testid="stMetricValue"] { direction: ltr; text-align: right; font-weight: bold; }
        [data-testid="stMetricLabel"] { text-align: right; }

        /* Input Fields */
        .stTextInput input, .stTextArea textarea { direction: rtl; text-align: right; }

        /* Sidebar */
        [data-testid="stSidebar"] { direction: rtl; text-align: right; }

        /* Container borders */
        [data-testid="stVerticalBlock"] > div:has(> div.element-container) {
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def save_scenario(markdown_text: str) -> tuple[bool, str]:
    """
    Parse scenario markdown and save it to the database.

    Args:
        markdown_text: The scenario text in markdown format

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info("Starting scenario save process")

        # Parse the markdown to get scenario data
        scenario_data = parse_md_to_scenario(markdown_text)
        logger.debug(f"Parsed scenario data: title={scenario_data.get('title')}, category={scenario_data.get('category')}")

        # Insert into database
        row_id = insert_scenario(
            data=scenario_data,
            owner="streamlit",
            pending=True  # Mark for review
        )

        logger.info(f"Scenario saved successfully with ID: {row_id}")
        return True, f"✅ Scenario saved successfully! Database ID: {row_id}"

    except ValueError as e:
        # Handle validation errors (missing fields, duplicates, etc.)
        error_msg = str(e)
        logger.warning(f"Validation error during save: {error_msg}")

        if "already exists" in error_msg.lower():
            return False, f"❌ Error: A scenario with this title already exists."
        elif "required" in error_msg.lower():
            return False, f"❌ Error: {error_msg}"
        elif "unknown category" in error_msg.lower():
            return False, f"❌ Error: Invalid category. Please check the scenario metadata."
        else:
            return False, f"❌ Validation Error: {error_msg}"

    except Exception as e:
        logger.error(f"Unexpected error during save: {str(e)}", exc_info=True)
        return False, f"❌ Unexpected error: {str(e)}"


def save_chat_log(messages: list[dict], title: str = None) -> tuple[bool, str]:
    """
    Save chat conversation log to a JSON file.

    Args:
        messages: List of message dicts with 'role' and 'content'
        title: Optional title for the chat log

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info(f"Starting chat log save process for {len(messages)} messages")

        # Create logs directory if it doesn't exist
        logs_dir = Path(config_trinity.BASE_DIR) / "chat_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_{timestamp}.json"
        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"chat_{timestamp}_{safe_title[:50]}.json"

        filepath = logs_dir / filename

        # Save chat log
        chat_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title or "Untitled Chat",
            "messages": messages,
            "message_count": len(messages)
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Chat log saved successfully to: {filepath}")
        return True, f"✅ Chat log saved to: {filepath.name}"

    except Exception as e:
        logger.error(f"Error saving chat log: {str(e)}", exc_info=True)
        return False, f"❌ Error saving chat log: {str(e)}"


# ============================================================================
# VIEW FUNCTIONS
# ============================================================================

def home_view():
    """Operational Dashboard - Hebrew metrics-based view."""
    st.title("🏠 מרכז שליטה - תתל״מ Trinity")
    st.markdown("---")

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)

    # Metric 1: Scenarios in gold_md
    with col1:
        gold_dir = Path(config_trinity.GOLD_DIR)
        if gold_dir.exists() and gold_dir.is_dir():
            md_files = list(gold_dir.glob("*.md"))
            count = len(md_files)
        else:
            count = 0
        st.metric("תרחישים במאגר", count, delta=None)

    # Metric 2: Pending scenarios in DB
    with col2:
        try:
            pending_scenarios = get_db_scenarios("pending")
            pending_count = len(pending_scenarios)
        except:
            pending_count = 0
        st.metric("ממתינים לאישור", pending_count, delta=None)

    # Metric 3: Brain status
    with col3:
        if "brain" in st.session_state:
            status = "מחובר ✓"
            delta_color = "normal"
        else:
            status = "מנותק"
            delta_color = "off"
        st.metric("סטטוס מוח", status, delta=None)

    # Metric 4: Local model
    with col4:
        model_short = config_trinity.LOCAL_MODEL_NAME.split("-")[0].upper()  # "QWEN"
        st.metric("מודל מקומי", model_short, delta="2.5-32B")

    st.markdown("---")

    # System architecture overview
    st.subheader("🎯 ארכיטקטורת המערכת")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.info("""
        **🖊️ הכותב (Writer)**

        Claude Sonnet 4.5

        תפקיד: יצירת תרחישי אימון מציאותיים
        """)

    with col_b:
        st.info("""
        **⚖️ השופט (Judge)**

        Gemini 2.0 Pro

        תפקיד: ביקורת ודירוג ביצועים
        """)

    with col_c:
        st.info("""
        **💬 הסימולטור (Simulator)**

        Qwen 2.5 32B (Local)

        תפקיד: גילום יריבים ואזרחים
        """)

    st.markdown("---")

    # Quick status checks
    st.subheader("📊 סטטוס מערכות")

    status_col1, status_col2 = st.columns(2)

    with status_col1:
        if config_trinity.ANTHROPIC_API_KEY:
            st.success("✓ Anthropic API - מחובר")
        else:
            st.error("✗ Anthropic API - מנותק")

    with status_col2:
        if config_trinity.GOOGLE_API_KEY:
            st.success("✓ Google API - מחובר")
        else:
            st.error("✗ Google API - מנותק")


def generate_scenario_view():
    """Hebrew scenario generation interface."""
    st.title("⚡ מחולל תרחישים - הכותב")
    st.markdown("---")

    # Initialize the brain
    if "brain" not in st.session_state:
        with st.spinner("מאתחל מערכת Trinity..."):
            try:
                st.session_state.brain = TrinityBrain()
            except Exception as e:
                st.error(f"כשל באתחול המוח: {e}")
                return

    brain = st.session_state.brain

    # Prompt input (Hebrew)
    st.subheader("הנחיות לתרחיש")
    prompt = st.text_area(
        "תאר את התרחיש הרצוי:",
        height=150,
        placeholder="דוגמה: צור תרחיש אבטחה הכולל חבילה חשודה שנמצאה ברציף הרכבת...",
        help="תאר בפירוט את התרחיש שברצונך שהמערכת תייצר. ציין הקשר, רמת סיכון ופרטים נדרשים."
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        generate_button = st.button("🚀 צור תרחיש", type="primary", use_container_width=True)

    with col2:
        if st.button("🗑️ נקה", use_container_width=True):
            if "last_scenario" in st.session_state:
                del st.session_state.last_scenario
            if "scenario_prompt" in st.session_state:
                del st.session_state.scenario_prompt
            st.rerun()

    # Generate scenario
    if generate_button and prompt:
        logger.info(f"User requested scenario generation with prompt: {prompt[:100]}...")
        st.markdown("---")
        st.subheader("תרחיש שנוצר")

        try:
            # Stream the generation
            scenario_text = st.write_stream(brain.generate_scenario_stream(prompt))

            # Store in session state
            st.session_state.last_scenario = scenario_text
            st.session_state.scenario_prompt = prompt
            logger.info(f"Scenario generated successfully, length: {len(scenario_text)} characters")

        except Exception as e:
            logger.error(f"Error generating scenario: {e}", exc_info=True)
            st.error(f"❌ שגיאה ביצירת תרחיש: {e}")
            return

    # Display saved scenario and actions
    if "last_scenario" in st.session_state:
        st.markdown("---")
        st.subheader("פעולות")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 שמור למאגר", type="primary", use_container_width=True):
                with st.spinner("שומר תרחיש..."):
                    success, message = save_scenario(st.session_state.last_scenario)
                    if success:
                        st.success(message)
                        st.balloons()
                        logger.info("Scenario saved successfully, showing balloons")

                        # Option to clear for next scenario
                        st.info("💡 תרחיש נשמר! ניתן לייצר תרחיש חדש או להמשיך לערוך.")
                    else:
                        st.error(message)
                        logger.error(f"Failed to save scenario: {message}")

        with col2:
            if st.button("⚖️ ביקורת שופט", use_container_width=True):
                logger.info("User requested scenario audit")
                with st.spinner("מבצע ביקורת..."):
                    try:
                        audit_result = brain.audit_scenario(st.session_state.last_scenario)
                        st.info("**תוצאות ביקורת:**")
                        st.markdown(audit_result)
                        logger.info("Scenario audit completed successfully")
                    except Exception as e:
                        logger.error(f"Audit failed: {e}", exc_info=True)
                        st.error(f"❌ הביקורת נכשלה: {e}")

        with col3:
            if st.button("📋 העתק טקסט", use_container_width=True):
                st.code(st.session_state.last_scenario, language="markdown")
                st.caption("בחר את הטקסט והעתק ידנית")

        # Show the last generated scenario
        st.markdown("---")
        st.subheader("תרחיש אחרון שנוצר")
        with st.expander("הצג תרחיש", expanded=False):
            st.markdown(st.session_state.last_scenario)


def get_db_scenarios(status_filter: str = "all") -> list[dict]:
    """
    Fetch scenarios from database with optional status filtering.

    Args:
        status_filter: "all", "pending", or "approved"

    Returns:
        List of scenario dictionaries
    """
    import sqlite3
    from tatlam.infra.repo import normalize_row

    try:
        db_path = config_trinity.DB_PATH
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        if status_filter == "all":
            cur.execute(f"SELECT * FROM {config_trinity.TABLE_NAME} ORDER BY id DESC")
        elif status_filter == "pending":
            cur.execute(f"SELECT * FROM {config_trinity.TABLE_NAME} WHERE status='pending' ORDER BY id DESC")
        elif status_filter == "approved":
            cur.execute(f"SELECT * FROM {config_trinity.TABLE_NAME} WHERE status='approved' ORDER BY id DESC")
        else:
            cur.execute(f"SELECT * FROM {config_trinity.TABLE_NAME} ORDER BY id DESC")

        rows = [normalize_row(x) for x in cur.fetchall()]
        con.close()
        return rows
    except Exception as e:
        logger.error(f"Error fetching scenarios from DB: {e}", exc_info=True)
        return []


def catalog_view():
    """Hebrew card-based catalog view."""
    st.title("📚 ארכיון מבצעי - תיקי תרחישים")
    st.markdown("---")

    # Get gold_md files
    gold_dir = Path(config_trinity.GOLD_DIR)

    if not gold_dir.exists():
        st.error(f"תיקיית ארכיון לא נמצאה: {gold_dir}")
        return

    md_files = list(gold_dir.glob("*.md"))

    if not md_files:
        st.warning("לא נמצאו תרחישים בארכיון.")
        return

    st.subheader(f"📊 סה״כ תרחישים: {len(md_files)}")
    st.markdown("---")

    # Session state for selected scenario
    if "selected_scenario_path" not in st.session_state:
        st.session_state.selected_scenario_path = None

    # Grid layout - 3 cards per row
    scenarios_data = []
    for file_path in sorted(md_files):
        try:
            content = file_path.read_text(encoding="utf-8")
            meta = parse_md_to_scenario(content)
            scenarios_data.append({"path": file_path, "meta": meta, "content": content})
        except Exception as e:
            logger.warning(f"Failed to parse {file_path.name}: {e}")
            continue

    # Display cards in grid
    for idx in range(0, len(scenarios_data), 3):
        cols = st.columns(3)

        for col_idx, col in enumerate(cols):
            if idx + col_idx < len(scenarios_data):
                scenario = scenarios_data[idx + col_idx]
                meta = scenario["meta"]
                file_path = scenario["path"]

                with col:
                    with st.container(border=True):
                        st.subheader(meta.get('title', 'ללא שם')[:40])
                        st.caption(f"📁 קטגוריה: {meta.get('category', 'כללי')}")
                        st.caption(f"⚠️ רמת סיכון: {meta.get('threat_level', 'לא ידוע')}")

                        if st.button("📂 פתח תיק", key=f"open_{file_path.name}", use_container_width=True):
                            st.session_state.selected_scenario_path = file_path
                            st.rerun()

    # Display selected scenario details
    if st.session_state.selected_scenario_path:
        st.markdown("---")
        st.markdown("---")

        selected_path = st.session_state.selected_scenario_path
        selected_content = selected_path.read_text(encoding="utf-8")
        selected_meta = parse_md_to_scenario(selected_content)

        col_back, col_title = st.columns([1, 5])

        with col_back:
            if st.button("⬅️ חזרה", use_container_width=True):
                st.session_state.selected_scenario_path = None
                st.rerun()

        with col_title:
            st.title(f"📄 {selected_meta.get('title', 'ללא שם')}")

        # Metrics row
        metric_col1, metric_col2, metric_col3 = st.columns(3)

        with metric_col1:
            st.metric("קטגוריה", selected_meta.get("category", "כללי"))
        with metric_col2:
            st.metric("רמת סיכון", selected_meta.get("threat_level", "לא ידוע"))
        with metric_col3:
            st.metric("מורכבות", selected_meta.get("complexity", "לא ידוע"))

        st.markdown("---")

        # Full content display
        st.markdown(selected_content)


def simulation_view():
    """Hebrew chat simulation interface with avatars."""
    st.title("💬 חדר סימולציות - תחנת אלנבי")
    st.markdown("---")

    # Initialize the brain
    if "brain" not in st.session_state:
        with st.spinner("מאתחל מערכת Trinity..."):
            try:
                st.session_state.brain = TrinityBrain()
            except Exception as e:
                st.error(f"כשל באתחול המוח: {e}")
                return

    brain = st.session_state.brain

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history with avatars
    for message in st.session_state.messages:
        role = message["role"]
        if role == "user":
            with st.chat_message("user", avatar="👮‍♂️"):
                st.markdown(message["content"])
        elif role == "assistant":
            with st.chat_message("assistant", avatar="👤"):
                st.markdown(message["content"])

    # Chat input (Hebrew placeholder)
    if prompt := st.chat_input("הקלד את הפעולה שלך כאן..."):
        logger.info(f"User sent chat message: {prompt[:100]}...")

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message with avatar
        with st.chat_message("user", avatar="👮‍♂️"):
            st.markdown(prompt)

        # Generate assistant response with streaming
        with st.chat_message("assistant", avatar="👤"):
            try:
                response = st.write_stream(brain.chat_simulation_stream(st.session_state.messages))

                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                logger.info(f"Assistant response generated, length: {len(response)} characters")

            except Exception as e:
                logger.error(f"Chat simulation error: {e}", exc_info=True)
                error_msg = f"שגיאה: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Sidebar controls for chat (Hebrew)
    with st.sidebar:
        st.markdown("### בקרת שיחה")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ נקה שיחה", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("💾 שמור לוג", use_container_width=True):
                if st.session_state.messages:
                    success, message = save_chat_log(st.session_state.messages)
                    if success:
                        st.success(message)
                        st.balloons()
                        logger.info("Chat log saved successfully, showing balloons")
                    else:
                        st.error(message)
                        logger.error(f"Failed to save chat log: {message}")
                else:
                    st.warning("אין הודעות לשמירה")

        st.markdown(f"**הודעות:** {len(st.session_state.messages)}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""

    # Apply RTL styling
    apply_rtl_style()

    # Sidebar navigation (Hebrew)
    st.sidebar.title("🎯 ניווט מערכת")

    view = st.sidebar.radio(
        "בחר תצוגה:",
        ["🏠 מרכז שליטה", "⚡ מחולל תרחישים", "📚 ארכיון מבצעי", "💬 סימולטור אימון"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### אודות")
    st.sidebar.info("מערכת Trinity - אימון ביטחוני מבוסס בינה מלאכותית")

    # Route to appropriate view
    if view == "🏠 מרכז שליטה":
        home_view()
    elif view == "⚡ מחולל תרחישים":
        generate_scenario_view()
    elif view == "📚 ארכיון מבצעי":
        catalog_view()
    elif view == "💬 סימולטור אימון":
        simulation_view()


if __name__ == "__main__":
    main()
