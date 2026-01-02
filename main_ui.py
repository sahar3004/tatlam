import streamlit as st
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
from typing import Any

# Logging setup
from tatlam.logging_setup import configure_logging
import logging

configure_logging()
logger = logging.getLogger(__name__)

# Trinity imports
from tatlam.core.brain import TrinityBrain
from tatlam.settings import get_settings

# Get settings instance
settings = get_settings()

# Persistence imports
from tatlam.infra.repo import insert_scenario
from tatlam.core.gold_md import parse_md_to_scenario

# Premium UI styles
from tatlam.ui.styles import get_full_stylesheet


# Page Configuration
st.set_page_config(
    page_title=settings.PAGE_TITLE,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# PREMIUM THEME APPLICATION
# ============================================================================

def apply_premium_theme() -> None:
    """Apply premium dark theme with RTL support and modern styling."""
    st.markdown(get_full_stylesheet(), unsafe_allow_html=True)


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


def save_chat_log(messages: list[dict[str, str]], title: str | None = None) -> tuple[bool, str]:
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
        logs_dir = settings.BASE_DIR / "chat_logs"
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

def home_view() -> None:
    """Operational Dashboard - Hebrew metrics-based view with premium styling."""
    st.title("🏠 מרכז שליטה - תתל״מ Trinity")
    st.markdown("---")

    # Metrics Row with enhanced styling
    col1, col2, col3, col4 = st.columns(4)

    # Metric 1: Scenarios in gold_md
    with col1:
        gold_dir = settings.GOLD_DIR
        if gold_dir.exists() and gold_dir.is_dir():
            md_files = list(gold_dir.glob("*.md"))
            count = len(md_files)
        else:
            count = 0
        st.metric("📁 תרחישים במאגר", count, delta=None)

    # Metric 2: Pending scenarios in DB
    with col2:
        try:
            pending_scenarios = get_db_scenarios("pending")
            pending_count = len(pending_scenarios)
        except Exception:
            pending_count = 0
        delta_str = "ממתינים" if pending_count > 0 else None
        st.metric("⏳ ממתינים לאישור", pending_count, delta=delta_str)

    # Metric 3: Brain status
    with col3:
        if "brain" in st.session_state:
            status = "מחובר ✓"
        else:
            status = "מנותק"
        st.metric("🧠 סטטוס מוח", status, delta=None)

    # Metric 4: Local scout model
    with col4:
        model_short = settings.LOCAL_MODEL_NAME.split("-")[0].upper()
        st.metric("🔭 סייר מקומי", model_short, delta="Qwen")

    st.markdown("---")

    # System architecture overview with enhanced cards
    st.subheader("🎯 ארכיטקטורת המערכת")

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        with st.container(border=True):
            st.markdown("""
            ### 🔭 הסיירים (Scouts)

            **Qwen (Local) + Claude Sonnet 4.5**

            תפקיד: סריקה וזיהוי איומים
            """)

    with col_b:
        with st.container(border=True):
            st.markdown("""
            ### 🖊️ הכותב (Writer)

            **Claude Sonnet 4.5**

            תפקיד: יצירת תרחישי אימון מציאותיים
            """)

    with col_c:
        with st.container(border=True):
            st.markdown("""
            ### ⚖️ השופט (Judge)

            **Claude Opus 4.5**

            תפקיד: ביקורת ודירוג ביצועים
            """)

    with col_d:
        with st.container(border=True):
            st.markdown("""
            ### 💬 הסימולטור (Simulator)

            **Gemini 3 Flash**
            
            תפקיד: גילום יריבים ואזרחים
            """)

    st.markdown("---")

    # Quick status checks with LED indicators
    st.subheader("📊 סטטוס מערכות")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        if settings.has_writer():
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(34, 197, 94, 0.1); border-radius: 8px; border: 1px solid rgba(34, 197, 94, 0.3);">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 10px #22c55e;"></div>
                <span style="color: #4ade80; font-weight: 500;">Anthropic API - מחובר</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 10px #ef4444;"></div>
                <span style="color: #f87171; font-weight: 500;">Anthropic API - מנותק</span>
            </div>
            """, unsafe_allow_html=True)

    with status_col2:
        if settings.has_judge():
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(34, 197, 94, 0.1); border-radius: 8px; border: 1px solid rgba(34, 197, 94, 0.3);">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 10px #22c55e;"></div>
                <span style="color: #4ade80; font-weight: 500;">Google API - מחובר</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 10px #ef4444;"></div>
                <span style="color: #f87171; font-weight: 500;">Google API - מנותק</span>
            </div>
            """, unsafe_allow_html=True)

    with status_col3:
        # Local scout model status (Qwen)
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
            <div style="width: 12px; height: 12px; border-radius: 50%; background: #3b82f6; box-shadow: 0 0 10px #3b82f6;"></div>
            <span style="color: #60a5fa; font-weight: 500;">סייר מקומי (Qwen) - מוגדר</span>
        </div>
        """, unsafe_allow_html=True)


def generate_scenario_view() -> None:
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

    # Tabs for generator modes
    tab1, tab2 = st.tabs(["🏗️ מחולל מובנה", "✍️ כתיבה חופשית"])

    # --- Mode 1: Structured Generation ---
    with tab1:
        st.info("🔹 בחר פרמטרים או השאר על 'אקראי' לאתגר מפתיע.")
        
        with st.form("structured_gen_form"):
            col1, col2 = st.columns(2, gap="large")
            
            with col1:
                venue_options = ["אקראי", "תחנת תת״ק", "תחנה עילית"]
                venue = st.selectbox("📍 זירה / מיקום", venue_options)
                
                role_options = ["אקראי", "מאבטח", "אופנוען"]
                role = st.selectbox("👮 תפקיד מתרגל", role_options)

            with col2:
                threat_options = [
                    "אקראי", 
                    "חפץ חשוד",
                    "פיגוע",
                    "פיגוע משולב",
                    "מטען ודאי",
                    "רכב תופת",
                    "רכב מתפרץ",
                    "רחפנים",
                    "חומ״ס/שריפה",
                    "סדר ציבורי",
                    "אירוע רפואי"
                ]
                category = st.selectbox("⚠️ סוג איום", threat_options)
                
                complexity = st.select_slider(
                    "רמת מורכבות",
                    options=["נמוכה", "בינונית", "גבוהה", "גבוהה מאוד"],
                    value="בינונית"
                )

            st.divider() # Visual separator

            extra_instructions = st.text_area(
                "הערות נוספות (אופציונלי)",
                placeholder="למשל: 'כלול אלמנט של לחץ זמן' או 'הוסף אזרח שמפריע לטיפול'",
                height=80
            )

            st.markdown("<br>", unsafe_allow_html=True) # Spacer before button

            submitted_structured = st.form_submit_button("🚀 צור תרחיש מובנה", type="primary", use_container_width=True)

        if submitted_structured:
            # Construct prompt from parameters
            prompt = (
                f"צור תרחיש אימון חדש ומפורט.\n"
                f"1. זירה: {venue}\n"
                f"2. תפקיד לתרגול: {role}\n"
                f"3. סוג איום מרכזי: {category}\n"
                f"4. רמת מורכבות: {complexity}\n"
            )
            if extra_instructions:
                prompt += f"5. דגשים נוספים: {extra_instructions}\n"
            
            prompt += "\nעליך להקפיד על יצירתיות, בטיחות, ועמידה בדוקטרינה.\n"
            if "אקראי" in [venue, role, category]:
                prompt += "עבור שדות שסומנו כ-'אקראי', בחר אפשרות מאתגרת ומגוונת שתפתיע את המתאמן.\n"

            # Map the Hebrew selection to internal venue code
            venue_ctx = "jaffa" if venue == "תחנה עילית" else "allenby"
            
            # Execute generation
            _execute_generation(brain, prompt, venue_context=venue_ctx)


    # --- Mode 2: Free Text Generation ---
    with tab2:
        with st.form("free_text_gen_form"):
            free_prompt = st.text_area(
                "תאר את התרחיש הרצוי או הדבק טקסט לשיפור:",
                height=200,
                placeholder="דוגמה: צור תרחיש אבטחה הכולל חבילה חשודה שנמצאה ברציף הרכבת, כאשר במקביל ישנה התראת צבע אדום...",
                help="תאר בפירוט את התרחיש שברצונך שהמערכת תייצר."
            )
            
            submitted_free = st.form_submit_button("🚀 צור / שפר תרחיש", type="primary", use_container_width=True)

        if submitted_free:
            if not free_prompt.strip():
                st.warning("נא להזין טקסט לפני השליחה.")
            else:
                # Naive check for context in free text
                venue_ctx = "jaffa" if "עילית" in free_prompt or "יפו" in free_prompt else "allenby"
                _execute_generation(brain, free_prompt, venue_context=venue_ctx)

    # --- Result Display ---
    if "last_scenario" in st.session_state:
        st.markdown("---")
        st.subheader("📝 תוצאה סופית")
        
        # Container for the result to give it visual weight
        with st.container(border=True):
            # Toolbar
            col_actions, col_copy = st.columns([3, 1])
            
            with col_actions:
                c1, c2, c3 = st.columns(3, gap="small")
                with c1:
                    if st.button("💾 שמור למאגר", use_container_width=True, help="שמור את התרחיש לארכיון המבצעי"):
                        with st.spinner("שומר..."):
                            success, message = save_scenario(st.session_state.last_scenario)
                            if success:
                                st.success("נשמר בהצלחה!")
                                st.balloons()
                            else:
                                st.error(message)

                with c2:
                    # Rejection with Popover (Streamlit 1.30+)
                    with st.popover("❌ דחה (ללמידה)", use_container_width=True, help="סמן כשגוי ותעד סיבה לשיפור המודל"):
                        st.markdown("##### 🗑️ דחיית תרחיש")
                        reason = st.text_input("סיבת הדחייה:", placeholder="לדוגמה: לא תואם דוקטרינה, מסוכן מדי...")
                        if st.button("אשר דחייה", type="primary", use_container_width=True):
                            if reason.strip():
                                # We need an ID to reject. If it wasn't saved yet, we act as if we reject the 'concept'.
                                # But for the 'learning loop', we probably want to save it with status='rejected'.
                                # So, let's save it strictly as rejected.
                                try:
                                    # Reuse save logic but force status
                                    data = parse_md_to_scenario(st.session_state.last_scenario)
                                    # Insert as rejected directly via repo
                                    from tatlam.infra.repo import get_repository
                                    repo = get_repository()
                                    # We simulate saving then updating, or just insert with a special flag if we had one.
                                    # Since insert_scenario defaults to pending, let's just insert then reject.
                                    # Optimization: Modify insert_scenario later to accept initial status, 
                                    # but for now "surgical" means use the tool we built.
                                    
                                    # 1. Insert (if not exists, or get ID) -> Wait, if we haven't saved, we don't have an ID.
                                    # We should save it as a "Rejected Candidate".
                                    # Let's use internal repo insert logic but manually.
                                    # Or simpler:
                                    row_id = repo.insert_scenario(data, pending=True) # Insert first
                                    _reject_scenario_handler(row_id, reason) # Then reject immediately
                                    
                                except Exception as e:
                                    st.error(f"שגיאה: {e}")
                            else:
                                st.warning("נא לכתוב סיבה.")

                with c3:
                    st.download_button(
                        "⬇️ קובץ להורדה",
                        data=st.session_state.last_scenario,
                        file_name=f"scenario_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

            # Display Audit Result if it exists
            if "audit_result" in st.session_state:
                with st.expander("⚖️ דו״ח ביקורת שיפוטית (לחץ לסגירה)", expanded=True):
                    st.markdown(st.session_state.audit_result)
                    if st.button("סגור דוח", key="close_audit"):
                        del st.session_state.audit_result
                        st.rerun()

            st.divider()
            
            # The Scenario Text
            st.markdown(st.session_state.last_scenario)


def _execute_generation(brain: TrinityBrain, prompt: str, venue_context: str = "allenby"):
    """Internal helper to execute generation and handle state."""
    logger.info(f"Generating scenario with prompt: {prompt[:100]}... Context: {venue_context}")
    
    st.markdown("---")
    st.subheader("🔄 מעבד נתונים...")
    
    try:
        # Stream the generation
        scenario_placeholder = st.empty()
        full_response = ""
        
        # Use st.spinner for the initial connection delay
        with st.spinner("המוח חושב... (Trinity Brain Processing)"):
            # Pass venue context to ensure correct Doctrine is loaded
            stream = brain.generate_scenario_stream(prompt, venue=venue_context)
            
            # Stream output chunks
            for chunk in stream:
                full_response += chunk
                scenario_placeholder.markdown(full_response + "▌")
                
        # Final render without cursor
        scenario_placeholder.markdown(full_response)

        # Update session state with generated text
        st.session_state.last_scenario = full_response
        st.session_state.scenario_prompt = prompt
        
        # --- Mandatory Judge Audit ---
        st.markdown("---")
        with st.status("⚖️ מבצע ביקורת שיפוטית (חובה)...", expanded=True) as status:
            try:
                st.write("מנתח עמידה בדוקטרינה...")
                audit_result = brain.audit_scenario(full_response)
                st.session_state.audit_result = audit_result
                status.update(label="✅ הביקורת הושלמה בהצלחה!", state="complete", expanded=False)
            except Exception as e:
                logger.error(f"Audit failed: {e}")
                st.session_state.audit_result = f"❌ כשל בביקורת: {e}"
                status.update(label="❌ הביקורת נכשלה", state="error")

        logger.info(f"Scenario generated and audited, length: {len(full_response)}")

    except Exception as e:
        logger.error(f"Error generating scenario: {e}", exc_info=True)
        st.error(f"❌ שגיאה ביצירת תרחיש: {e}")


def _reject_scenario_handler(sid: int, reason: str):
    """Handle scenario rejection."""
    from tatlam.infra.repo import get_repository
    repo = get_repository()
    
    if repo.reject_scenario(sid, reason):
        st.toast(f"התרחיש נדחה ונשמר ללמידה. סיבה: {reason}")
        # Clear session state to reset view
        if "last_scenario" in st.session_state:
            del st.session_state.last_scenario
        if "audit_result" in st.session_state:
            del st.session_state.audit_result
        st.rerun()
    else:
        st.error("שגיאה בדחיית התרחיש (לא נמצא ב-DB?)")



def get_db_scenarios(status_filter: str = "all") -> list[dict[str, Any]]:
    """
    Fetch scenarios from database with optional status filtering.
    Uses repo layer instead of raw SQL.

    Args:
        status_filter: "all", "pending", or "approved"

    Returns:
        List of scenario dictionaries
    """
    from tatlam.infra.repo import fetch_all

    try:
        # Fetch all scenarios from repo (already normalized)
        all_scenarios = fetch_all()

        # Filter by status if needed
        if status_filter == "pending":
            return [s for s in all_scenarios if s.get("status") == "pending"]
        elif status_filter == "approved":
            return [s for s in all_scenarios if s.get("status") == "approved"]
        else:
            # "all" - return everything
            return all_scenarios

    except Exception as e:
        logger.error(f"Error fetching scenarios from DB: {e}", exc_info=True)
        return []


def catalog_view() -> None:
    """Hebrew card-based catalog view."""
    st.title("📚 ארכיון מבצעי - תיקי תרחישים")
    st.markdown("---")

    # Get gold_md files
    gold_dir = settings.GOLD_DIR

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

                        # Category tag
                        category = meta.get('category', 'כללי')
                        st.markdown(f"""
                        <span style="display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 500; background: rgba(129, 140, 248, 0.15); color: #a5b4fc; border: 1px solid rgba(129, 140, 248, 0.3); margin-left: 8px;">
                            📁 {category}
                        </span>
                        """, unsafe_allow_html=True)

                        # Threat level with color coding
                        threat = meta.get('threat_level', 'לא ידוע')
                        if threat in ['גבוהה', 'גבוהה מאוד']:
                            badge_style = "background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3);"
                        elif threat == 'בינונית':
                            badge_style = "background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3);"
                        else:
                            badge_style = "background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.3);"

                        st.markdown(f"""
                        <span style="display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 500; {badge_style} border: 1px solid; margin-top: 8px;">
                            ⚠️ {threat}
                        </span>
                        """, unsafe_allow_html=True)

                        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

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


def simulation_view() -> None:
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

def main() -> None:
    """Main application entry point."""

    # Apply premium theme (includes RTL styling)
    apply_premium_theme()

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
