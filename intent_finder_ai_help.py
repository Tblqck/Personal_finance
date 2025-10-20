import os
import json
import requests

# ---------------- CONFIG ----------------
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "mistralai/mixtral-8x7b-instruct"

INTENT_CLASSES = [
    "add_income",
    "add_expense",
    "set_reminder",
    "correct_transaction",
    "generate_report",
    "chat"
]

# ---------------- MAIN FUNCTION ----------------
def detect_intent(message: str) -> str:
    """
    Sends a message to OpenRouter and classifies it into one of the predefined intents.
    Always returns ONE class from INTENT_CLASSES.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("❌ Missing OPENROUTER_API_KEY environment variable.")

    prompt = f"""
You are an intent classifier for a personal finance assistant.
Classify the user's message into EXACTLY one of the following intents:

{', '.join(INTENT_CLASSES)}

Definitions:
- add_income: user wants to record income or money received.
- add_expense: user wants to record spending or purchase.
- set_reminder: user wants to set or schedule a reminder.
- correct_transaction: user wants to edit, fix or delete a past record.
- generate_report: user wants a report, summary, or statistics of finances.
- chat: anything else or general conversation.

User message: "{message}"

Return only one of the intent labels (no explanation, no JSON, no extra text).
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a strict intent classifier."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0
    }

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        raw_output = data["choices"][0]["message"]["content"].strip().lower()

        # Match strictly to known intents
        for intent in INTENT_CLASSES:
            if intent in raw_output:
                return intent

        return "chat"  # fallback default intent

    except Exception as e:
        print("❌ Intent detection failed:", e)
        return "chat"
