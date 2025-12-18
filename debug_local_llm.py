#!/usr/bin/env python3
"""
Debug script for testing local Llama server connectivity.

This script verifies:
1. The local Llama server is running and accessible
2. The expected model name matches what the server exposes
3. The model can generate Hebrew text responses

Usage:
    python3 debug_local_llm.py
"""

import sys
from openai import OpenAI

# הגדרות (תואמות למה שקבענו)
BASE_URL = "http://127.0.0.1:8080/v1"
API_KEY = "sk-no-key-required"
EXPECTED_MODEL = "llama-3.3-70b-instruct"

print(f"🕵️  Checking connection to Local Llama at {BASE_URL}...")

try:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    # 1. בדיקת רשימת מודלים
    models = client.models.list()
    available_models = [m.id for m in models.data]
    print(f"✅ Server is UP! Available models: {available_models}")

    if EXPECTED_MODEL not in available_models:
        print(f"❌ ERROR: Config expects '{EXPECTED_MODEL}' but server has {available_models}")
        print("   -> Did you restart the ./scripts/start_local_llm.sh script after the update?")
        sys.exit(1)

    print(f"✅ Model '{EXPECTED_MODEL}' found.")

    # 2. בדיקת יצירת טקסט (עברית)
    print("💬 Sending test prompt in Hebrew...")
    response = client.chat.completions.create(
        model=EXPECTED_MODEL,
        messages=[
            {"role": "system", "content": "אתה עוזר נחמד."},
            {"role": "user", "content": "האם אתה מחובר ושומע אותי? תענה בקיצור."}
        ],
        temperature=0.7
    )

    answer = response.choices[0].message.content
    print(f"\n🤖 Llama Response:\n{'-'*20}\n{answer}\n{'-'*20}")
    print("\n🚀 SUCCESS: The local brain is fully connected and ready!")

except Exception as e:
    print(f"\n❌ CONNECTION FAILED: {e}")
    print("   -> Make sure you ran './scripts/start_local_llm.sh' in a separate terminal.")
    sys.exit(1)
