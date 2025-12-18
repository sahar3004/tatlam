#!/usr/bin/env python3
"""
Trinity System Status Checker
Verifies that all three AI models are accessible before launching the system.
"""

import os
import sys
from openai import OpenAI
import config_trinity


def check_env_variable(var_name: str, var_value: str | None) -> bool:
    """Check if an environment variable is set."""
    if var_value:
        print(f"✅ {var_name}: Configured")
        return True
    else:
        print(f"❌ {var_name}: Missing")
        return False


def check_local_server() -> bool:
    """Check if the local Qwen server is running and accessible."""
    try:
        print(f"\n🔍 Checking local server at {config_trinity.LOCAL_BASE_URL}...")

        client = OpenAI(
            base_url=config_trinity.LOCAL_BASE_URL,
            api_key=config_trinity.LOCAL_API_KEY
        )

        # Try to list models
        models = client.models.list()
        model_ids = [model.id for model in models.data]

        print(f"✅ Local server is running")
        print(f"   Available models: {', '.join(model_ids)}")

        # Check if the configured model is available
        if config_trinity.LOCAL_MODEL_NAME in model_ids:
            print(f"   ✅ Configured model '{config_trinity.LOCAL_MODEL_NAME}' is available")
            return True
        else:
            print(f"   ⚠️  Warning: Configured model '{config_trinity.LOCAL_MODEL_NAME}' not found in available models")
            print(f"   The server will use the first available model: {model_ids[0] if model_ids else 'none'}")
            return True  # Still return True if server is running

    except Exception as e:
        print(f"❌ Local server connection failed: {e}")
        print(f"   Make sure the server is running on {config_trinity.LOCAL_BASE_URL}")
        return False


def main():
    """Run all system checks."""
    print("=" * 60)
    print("🎭 TRINITY SYSTEM STATUS CHECK")
    print("=" * 60)

    results = []

    # Check 1: Writer (Claude via Anthropic)
    print("\n1️⃣  THE WRITER (Claude via Anthropic)")
    print(f"   Model: {config_trinity.WRITER_MODEL_NAME}")
    results.append(check_env_variable("ANTHROPIC_API_KEY", config_trinity.ANTHROPIC_API_KEY))

    # Check 2: Judge (Gemini via Google)
    print("\n2️⃣  THE JUDGE (Gemini via Google)")
    print(f"   Model: {config_trinity.JUDGE_MODEL_NAME}")
    results.append(check_env_variable("GOOGLE_API_KEY", config_trinity.GOOGLE_API_KEY))

    # Check 3: Simulator (Local Qwen)
    print("\n3️⃣  THE SIMULATOR (Local Qwen)")
    print(f"   Model: {config_trinity.LOCAL_MODEL_NAME}")
    results.append(check_local_server())

    # Database check
    print("\n4️⃣  DATABASE")
    from pathlib import Path
    db_path = Path(config_trinity.DB_PATH)
    if db_path.exists():
        print(f"✅ Database found at: {db_path}")
        results.append(True)
    else:
        print(f"⚠️  Database not found at: {db_path}")
        print(f"   It will be created on first use")
        results.append(True)  # Not a critical failure

    # Final verdict
    print("\n" + "=" * 60)
    if all(results):
        print("✅ READY TO LAUNCH")
        print("\nRun the system with:")
        print("  ./start_ui.sh")
        print("  OR")
        print("  streamlit run main_ui.py")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ SYSTEM NOT READY")
        print("\nPlease fix the issues above before launching.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
