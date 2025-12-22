import streamlit as st
import sys
import os
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# 1. Fix Imports - Ensure root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Page Config
st.set_page_config(
    page_title="Tatlam Mission Control",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🚀 Tatlam Mission Control")
st.caption("Hybrid AI Scenario Generator | System Status & Launchpad")

# 2. System Diagnostics
st.subheader("1. System Diagnostics")
col1, col2, col3 = st.columns(3)

checks_passed = True

# Check Environment
with col1:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv()
        # Verify keys exist
        required_keys = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"] # Basic keys
        missing = [k for k in required_keys if not os.getenv(k)]
        if missing:
             st.warning(f"⚠️ Missing keys: {missing}")
        else:
             st.success("✅ .env loaded")
    else:
        st.error("❌ .env missing")
        checks_passed = False

# Check Database
with col2:
    try:
        # Import inside to ensure path is set
        from tatlam.infra.db import init_db
        init_db() # Auto-run init
        st.success("✅ Database Connected")
    except Exception as e:
        st.error(f"❌ Database Error: {e}")
        checks_passed = False

# Check Local Brain
with col3:
    # User mandate: Ping http://localhost:8080/health
    ping_url = "http://localhost:8080/health"
    try:
        response = requests.get(ping_url, timeout=2.0)
        if response.status_code == 200:
            st.success("✅ Local Brain Active")
        else:
            st.warning(f"⚠️ Local Brain Status: {response.status_code}")
            # We don't fail check if just status code is weird, but warn. 
            # Ideally 200 OK means healthy.
            if response.status_code != 200:
                 checks_passed = False 
    except requests.exceptions.ConnectionError:
        st.error("❌ Local Brain OFFLINE")
        st.info("⚠️ Run: `llama-server -m ... --port 8080`")
        checks_passed = False
    except Exception as e:
        st.error(f"❌ Check Failed: {e}")
        checks_passed = False

if st.button("🔄 Re-run Checks"):
    st.rerun()

st.divider()

if not checks_passed:
    st.warning("⚠️ System checks failed. Please fix the issues above to launch the generator.")
    st.stop()

# 3. Hybrid Scenario Generator UI
try:
    from tatlam.core.brain import TrinityBrain
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.stop()

if "brain" not in st.session_state:
    with st.spinner("Initializing Trinity Brain..."):
        try:
            # Auto-initialize reads settings and env
            st.session_state.brain = TrinityBrain(auto_initialize=True)
        except Exception as e:
            st.error(f"Brain Init Failed: {e}")
            st.stop()

brain = st.session_state.brain

st.header("Hybrid Scenario Generator")
col_input, col_output = st.columns([1, 2])

with col_input:
    with st.form("scenario_input"):
        topic = st.text_area("Scenario Topic / Prompt", "Suspicious bag at train station platform", height=100)
        category = st.selectbox("Category", ["Security", "Safety", "Medical", "Service"])
        threat_level = st.select_slider("Threat Level", ["Low", "Medium", "High", "Critical"])
        
        submitted = st.form_submit_button("🚀 Generate Scenario", use_container_width=True)

if submitted:
    with col_output:
        status_container = st.status("Mission in Progress...", expanded=True)
        
        try:
            # Phase 1: Draft (Local)
            status_container.write("🧠 Phase 1: Structural Drafting (Local Engine)...")
            prompt = f"Category: {category}\nThreat Level: {threat_level}\nTopic: {topic}"
            
            # Using generate_draft
            draft = brain.generate_draft(prompt)
            status_container.write("✅ Draft Generated")
            with st.expander("View Draft Structure"):
                st.json(draft)

            # Phase 2: Refine (Cloud)
            status_container.write("☁️ Phase 2: Content Refinement (Cloud Engine)...")
            final_scenario = brain.refine_scenario(draft)
            status_container.write("✅ Refinement Complete")
            
            status_container.update(label="Mission Complete!", state="complete", expanded=False)
            
            st.subheader("Generated Scenario")
            st.markdown(final_scenario)
            
            # Option to save? (Maybe later) 
            
        except Exception as e:
            status_container.update(label="Mission Failed", state="error")
            st.error(f"Error during generation: {e}")
            import traceback
            st.code(traceback.format_exc())
