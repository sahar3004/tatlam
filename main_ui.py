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
    """Display the home page with welcome message and system status."""
    st.title("🎭 Tatlam Trinity System")
    st.markdown("---")

    st.markdown("""
    ### Welcome to the Trinity Architecture

    This system uses three specialized AI models working together:

    - **🖊️ The Writer (Claude)**: Generates high-quality scenarios using streaming
    - **⚖️ The Judge (Gemini)**: Audits and evaluates content quality
    - **💬 The Simulator (Local Llama)**: Handles interactive chat simulations
    """)

    st.markdown("---")
    st.subheader("System Status")

    # Check gold_md directory
    gold_dir = Path(config_trinity.GOLD_DIR)
    if gold_dir.exists() and gold_dir.is_dir():
        md_files = list(gold_dir.glob("*.md"))
        st.success(f"✓ Gold examples directory found: {len(md_files)} markdown files available")
    else:
        st.warning(f"⚠️ Gold examples directory not found at: {gold_dir}")

    # Check database
    db_path = Path(config_trinity.DB_PATH)
    if db_path.exists():
        st.success(f"✓ Database found: {db_path}")
    else:
        st.warning(f"⚠️ Database not found at: {db_path}")

    # Check configuration
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**Writer Model**\n\n{config_trinity.WRITER_MODEL_NAME}")
        if config_trinity.ANTHROPIC_API_KEY:
            st.caption("✓ API Key configured")
        else:
            st.caption("⚠️ API Key missing")

    with col2:
        st.info(f"**Judge Model**\n\n{config_trinity.JUDGE_MODEL_NAME}")
        if config_trinity.GOOGLE_API_KEY:
            st.caption("✓ API Key configured")
        else:
            st.caption("⚠️ API Key missing")

    with col3:
        st.info(f"**Simulator Model**\n\n{config_trinity.LOCAL_MODEL_NAME}")
        st.caption(f"Local server: {config_trinity.LOCAL_BASE_URL}")


def generate_scenario_view():
    """Generate new scenarios using Claude with streaming and save to database."""
    st.title("🖊️ Generate Scenario")
    st.markdown("---")

    # Initialize the brain
    if "brain" not in st.session_state:
        with st.spinner("Initializing Trinity Brain..."):
            try:
                st.session_state.brain = TrinityBrain()
            except Exception as e:
                st.error(f"Failed to initialize Trinity Brain: {e}")
                return

    brain = st.session_state.brain

    # Prompt input
    st.subheader("Scenario Prompt")
    prompt = st.text_area(
        "Enter your scenario generation prompt:",
        height=150,
        placeholder="Example: Create a security scenario involving a suspicious package found on a train platform...",
        help="Describe the scenario you want Claude to generate. Be specific about context, threat level, and desired details."
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        generate_button = st.button("🚀 Generate", type="primary", use_container_width=True)

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            if "last_scenario" in st.session_state:
                del st.session_state.last_scenario
            if "scenario_prompt" in st.session_state:
                del st.session_state.scenario_prompt
            st.rerun()

    # Generate scenario
    if generate_button and prompt:
        logger.info(f"User requested scenario generation with prompt: {prompt[:100]}...")
        st.markdown("---")
        st.subheader("Generated Scenario")

        try:
            # Stream the generation
            scenario_text = st.write_stream(brain.generate_scenario_stream(prompt))

            # Store in session state
            st.session_state.last_scenario = scenario_text
            st.session_state.scenario_prompt = prompt
            logger.info(f"Scenario generated successfully, length: {len(scenario_text)} characters")

        except Exception as e:
            logger.error(f"Error generating scenario: {e}", exc_info=True)
            st.error(f"❌ Error generating scenario: {e}")
            return

    # Display saved scenario and actions
    if "last_scenario" in st.session_state:
        st.markdown("---")
        st.subheader("Actions")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 Save Scenario to DB", type="primary", use_container_width=True):
                with st.spinner("Saving scenario..."):
                    success, message = save_scenario(st.session_state.last_scenario)
                    if success:
                        st.success(message)
                        st.balloons()  # Visual celebration
                        logger.info("Scenario saved successfully, showing balloons")

                        # Option to clear for next scenario
                        st.info("💡 Scenario saved! You can now generate a new one or continue editing.")
                    else:
                        st.error(message)
                        logger.error(f"Failed to save scenario: {message}")

        with col2:
            if st.button("⚖️ Audit with Judge", use_container_width=True):
                logger.info("User requested scenario audit")
                with st.spinner("Auditing scenario..."):
                    try:
                        audit_result = brain.audit_scenario(st.session_state.last_scenario)
                        st.info("**Audit Results:**")
                        st.markdown(audit_result)
                        logger.info("Scenario audit completed successfully")
                    except Exception as e:
                        logger.error(f"Audit failed: {e}", exc_info=True)
                        st.error(f"❌ Audit failed: {e}")

        with col3:
            if st.button("📋 Copy to Clipboard", use_container_width=True):
                st.code(st.session_state.last_scenario, language="markdown")
                st.caption("Select the text above and copy it manually")

        # Show the last generated scenario
        st.markdown("---")
        st.subheader("Last Generated Scenario")
        with st.expander("View Scenario", expanded=False):
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
    """Display the scenario catalog with file browser and database view."""
    st.title("📚 Scenario Catalog")
    st.markdown("---")

    # Source selector
    source = st.radio(
        "Select Source:",
        ["📁 Gold Files (gold_md)", "🗄️ Database Scenarios"],
        horizontal=True
    )

    st.markdown("---")

    if source == "📁 Gold Files (gold_md)":
        # Original gold_md file browser
        gold_dir = Path(config_trinity.GOLD_DIR)

        if not gold_dir.exists():
            st.error(f"Gold examples directory not found at: {gold_dir}")
            return

        # Get all markdown files
        md_files = list(gold_dir.glob("*.md"))

        if not md_files:
            st.warning("No markdown files found in the gold examples directory.")
            return

        st.write(f"Found {len(md_files)} scenario files")

        # Create a dataframe with file information
        file_data = []
        for file_path in sorted(md_files):
            file_data.append({
                "Filename": file_path.name,
                "Size (KB)": round(file_path.stat().st_size / 1024, 2),
                "Path": str(file_path)
            })

        df = pd.DataFrame(file_data)

        # Display the dataframe
        st.dataframe(df[["Filename", "Size (KB)"]], use_container_width=True, hide_index=True)

        st.markdown("---")

        # File selector
        selected_file = st.selectbox(
            "Select a file to view:",
            options=md_files,
            format_func=lambda x: x.name
        )

        if selected_file:
            st.subheader(f"📄 {selected_file.name}")

            try:
                content = selected_file.read_text(encoding="utf-8")

                # Display content in markdown
                with st.container():
                    st.markdown(content)

            except Exception as e:
                st.error(f"Error reading file: {e}")

    else:
        # Database view with status filtering
        st.subheader("Filter by Status")

        status_filter = st.selectbox(
            "Status:",
            ["all", "pending", "approved"],
            format_func=lambda x: {
                "all": "🔄 All Scenarios",
                "pending": "⏳ Pending Review",
                "approved": "✅ Approved"
            }[x]
        )

        scenarios = get_db_scenarios(status_filter)

        if not scenarios:
            st.warning("No scenarios found in database.")
            return

        st.write(f"Found {len(scenarios)} scenarios")

        # Create dataframe
        df_data = []
        for sc in scenarios:
            df_data.append({
                "ID": sc.get("id"),
                "Title": sc.get("title", "Untitled"),
                "Category": sc.get("category", "Unknown"),
                "Status": sc.get("status", "unknown"),
                "Owner": sc.get("owner", "unknown"),
                "Created": sc.get("created_at", "")[:10] if sc.get("created_at") else ""
            })

        df = pd.DataFrame(df_data)

        # Display dataframe with color coding
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Approval status"
                ),
                "Title": st.column_config.TextColumn(
                    "Title",
                    width="large"
                )
            }
        )

        st.markdown("---")

        # Scenario selector
        selected_id = st.selectbox(
            "Select a scenario to view:",
            options=[sc["id"] for sc in scenarios],
            format_func=lambda x: next((sc["title"] for sc in scenarios if sc["id"] == x), str(x))
        )

        if selected_id:
            selected_scenario = next((sc for sc in scenarios if sc["id"] == selected_id), None)

            if selected_scenario:
                st.subheader(f"📄 {selected_scenario.get('title', 'Untitled')}")

                # Status badge
                status = selected_scenario.get("status", "unknown")
                if status == "approved":
                    st.success(f"✅ Status: Approved")
                elif status == "pending":
                    st.warning(f"⏳ Status: Pending Review")
                else:
                    st.info(f"Status: {status}")

                # Display metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Category", selected_scenario.get("category", "Unknown"))
                with col2:
                    st.metric("Threat Level", selected_scenario.get("threat_level", "Unknown"))
                with col3:
                    st.metric("Complexity", selected_scenario.get("complexity", "Unknown"))

                st.markdown("---")

                # Display full scenario content
                with st.container():
                    st.markdown(f"**📋 Background:**")
                    st.write(selected_scenario.get("background", "N/A"))

                    st.markdown(f"**🎯 Response Steps:**")
                    steps = selected_scenario.get("steps", [])
                    if isinstance(steps, list):
                        for i, step in enumerate(steps, 1):
                            st.write(f"{i}. {step}")
                    else:
                        st.write(steps)

                    if selected_scenario.get("operational_background"):
                        st.markdown(f"**🎥 Operational Background:**")
                        st.write(selected_scenario.get("operational_background"))


def simulation_view():
    """Interactive chat simulation interface with streaming."""
    st.title("💬 Chat Simulation")
    st.markdown("---")

    # Initialize the brain
    if "brain" not in st.session_state:
        with st.spinner("Initializing Trinity Brain..."):
            try:
                st.session_state.brain = TrinityBrain()
            except Exception as e:
                st.error(f"Failed to initialize Trinity Brain: {e}")
                return

    brain = st.session_state.brain

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        logger.info(f"User sent chat message: {prompt[:100]}...")

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response with streaming
        with st.chat_message("assistant"):
            try:
                response = st.write_stream(brain.chat_simulation_stream(st.session_state.messages))

                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                logger.info(f"Assistant response generated, length: {len(response)} characters")

            except Exception as e:
                logger.error(f"Chat simulation error: {e}", exc_info=True)
                error_msg = f"Error: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Sidebar controls for chat
    with st.sidebar:
        st.markdown("### Chat Controls")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("💾 Save Log", use_container_width=True):
                if st.session_state.messages:
                    success, message = save_chat_log(st.session_state.messages)
                    if success:
                        st.success(message)
                        st.balloons()  # Visual celebration
                        logger.info("Chat log saved successfully, showing balloons")
                    else:
                        st.error(message)
                        logger.error(f"Failed to save chat log: {message}")
                else:
                    st.warning("No messages to save")

        st.markdown(f"**Messages:** {len(st.session_state.messages)}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""

    # Sidebar navigation
    st.sidebar.title("Navigation")

    view = st.sidebar.radio(
        "Select View:",
        ["Home", "Generate Scenario", "Scenario Catalog", "Simulation"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info("Tatlam Trinity System - AI-powered scenario generation and simulation")

    # Route to appropriate view
    if view == "Home":
        home_view()
    elif view == "Generate Scenario":
        generate_scenario_view()
    elif view == "Scenario Catalog":
        catalog_view()
    elif view == "Simulation":
        simulation_view()


if __name__ == "__main__":
    main()
