# ----------------- Local Intent Router with Sections -----------------
import json
import re
import requests
from income_core import handle_income, load_json, USER_DATA_FILE, BUDGET_JSON
from expencies_core import handle_expense
from set_reminder_core import single_reminder_call
# from record_edit import handle_record_edit  # Placeholder
from finance_reports_displayname_fixed import ai_interface  # For finance reports
from intent_finder_ai_help import detect_intent  # <-- AI-powered intent classifier

# ----------------- AI Config -----------------
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "mistralai/mixtral-8x7b-instruct"

# ======================================================
# 🧹 CLEAN TEXT EXTRACTOR — ensures clean Telegram output
# ======================================================
def extract_clean_text(response):
    """
    Extracts readable text from any structured AI or JSON response.
    Handles dict, list, and string formats safely.
    """
    try:
        # Case 1: If it's already a dict with 'message' key
        if isinstance(response, dict):
            if "message" in response:
                return str(response["message"])
            elif "content" in response:
                content = response["content"]
                if isinstance(content, list) and len(content) > 0:
                    return content[0].get("text", str(response))
                return str(content)

        # Case 2: If it's a list (like OpenRouter structured reply)
        elif isinstance(response, list):
            if len(response) > 0 and isinstance(response[0], dict):
                return response[0].get("content", [{}])[0].get("text", str(response))
            return str(response)

        # Case 3: If it's a JSON string
        elif isinstance(response, str) and response.strip().startswith("["):
            data = json.loads(response)
            if isinstance(data, list):
                return data[0].get("content", [{}])[0].get("text", response)
            return str(data)

        # Default fallback
        return str(response)
    except Exception:
        return str(response)

# ----------------- AI Chat Fallback (Smart + Open) -----------------
def ai_chat_fallback(message: str):
    """
    A flexible AI fallback that supports both general chat and finance context.
    It keeps awareness of being part of a finance assistant but doesn't force finance-only replies.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """
You are an intelligent, friendly assistant embedded inside a personal finance management bot.
You can freely discuss general topics (e.g., tech, weather, motivation, economy, culture) while staying conversational and human-like.

When the user discusses money, savings, income, expenses, budgeting, or balance —
gently suggest using the proper finance action (add_income, add_expense, generate_report, set_reminder, etc.)
but DO NOT force it. Otherwise, just continue the chat naturally.

Always stay concise, helpful, and friendly.
"""

    payload = {
        "model": AI_MODEL,
        "input": f"{system_prompt}\n\nUser: {message}\nAssistant:",
        "temperature": 0.6,
        "max_output_tokens": 400
    }

    try:
        response = requests.post(f"{OPENROUTER_BASE_URL}/responses", headers=headers, json=payload)
        data = response.json()

        # Handle different OpenRouter response structures
        if "output" in data:
            return extract_clean_text(data["output"])
        elif "data" in data and isinstance(data["data"], list):
            return extract_clean_text(data["data"][0].get("content", "🤖 Sorry, I couldn’t generate a valid reply."))
        else:
            return "🤖 Sorry, I couldn’t generate a valid response."
    except Exception as e:
        return f"🤖 AI fallback failed: {str(e)}"

# ----------------- Intent Handlers -----------------
def handle_user_intent(user_id, intent, message, user_data=None):
    user_data = user_data or load_json(USER_DATA_FILE)
    user_data.setdefault(user_id, {"sections": {}, "income": [], "expenses": [], "session_info": {}})

    if intent == "add_income":
        return {"message": extract_clean_text(handle_income(user_id, message, user_data))}

    elif intent == "add_expense":
        return {"message": extract_clean_text(handle_expense(user_id, message, user_data))}

    elif intent == "set_reminder":
        return {"message": extract_clean_text({"message": single_reminder_call(user_id, message)})}

    elif intent == "correct_transaction":
        return {"message": "🚧 Transaction edit/delete feature is under development. Stay tuned!"}

    elif intent == "generate_report":
        result = ai_interface(message, user_id=user_id)
        # ✅ Preserve both the summary and the PDF
        if isinstance(result, dict) and "summary" in result and "pdf" in result:
            return {
                "message": extract_clean_text(result["summary"]),
                "pdf": result["pdf"]
            }
        elif isinstance(result, dict):
            return {"message": extract_clean_text(result.get("summary", result))}
        return {"message": extract_clean_text(result)}

    elif intent == "chat":
        return {"message": extract_clean_text(ai_chat_fallback(message))}

    else:
        return {"message": "🤖 I didn’t understand that."}

# ----------------- Main Intent Router -----------------
def find_intent(user_id, message):
    user_data = load_json(USER_DATA_FILE)
    user_data.setdefault(user_id, {"sections": {}, "income": [], "expenses": [], "session_info": {}})

    sections = user_data[user_id].get("sections", {})

    # 1️⃣ Check active section first
    for section, status in sections.items():
        if status == "on":
            if section == "add_income":
                return {"intent": "add_income", "response": {"message": extract_clean_text(handle_income(user_id, message, user_data))}}
            elif section == "add_expense":
                return {"intent": "add_expense", "response": {"message": extract_clean_text(handle_expense(user_id, message, user_data))}}
            elif section == "set_reminder":
                return {"intent": "set_reminder", "response": {"message": extract_clean_text({"message": single_reminder_call(user_id, message)})}}
            elif section == "correct_transaction":
                return {"intent": "correct_transaction", "response": {"message": "🚧 Transaction edit/delete feature is under development. Stay tuned!"}}

    # 2️⃣ Detect intent using AI helper
    intent = detect_intent(message)

    # 3️⃣ Route to proper handler
    return {
        "intent": intent,
        "response": handle_user_intent(user_id, intent, message, user_data)
    }
