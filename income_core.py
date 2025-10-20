import re
import json
import os
import hashlib
import requests
from datetime import datetime

# ----------------------
# CONFIG
# ----------------------
USER_DATA_FILE = "user_data.json"
BUDGET_JSON = "budget.json"
RETRY_TRACKER_FILE = "retry_tracker.json"

CATEGORIES = [
    "salary", "bonus", "investment", "gift", "other"
]

CURRENCY_MAP = {
    "ngn": "NGN", "naira": "NGN", "₦": "NGN",
    "usd": "USD", "dollar": "USD", "$": "USD",
    "eur": "EUR", "€": "EUR",
}

OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "mistralai/mixtral-8x7b-instruct"

# ----------------------
# UTILS
# ----------------------
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def call_openrouter(prompt: str):
    """Call OpenRouter to generate AI response."""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "You are a concise finance assistant."},
                {"role": "user", "content": prompt}
            ],
        }
        r = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, str(e)

def extract_amount_currency(text):
    """Extract numeric amount and currency from text."""
    text_lower = text.lower()
    amount = None
    currency = None

    for k, v in CURRENCY_MAP.items():
        if k in text_lower:
            currency = v
            break

    m = re.search(r"(\d[\d,\.]*)", text.replace(",", ""))
    if m:
        amount = re.sub(r"[^\d]", "", m.group(1))
    return amount, currency

def predict_category(text):
    """Predict income category using AI."""
    cat_prompt = f"""
Classify this income into ONE simple category word or phrase from:
{', '.join(CATEGORIES)}.
Reply ONLY with ONE category word.
Income: {text}
"""
    resp, err = call_openrouter(cat_prompt)
    if not resp or err:
        return "other"
    resp = re.sub(r"```.*?```", "", resp, flags=re.DOTALL).replace('\n', ' ').strip().lower()
    for cat in CATEGORIES:
        if cat in resp:
            return cat
    return "other"

# ----------------------
# HANDLE INCOME
# ----------------------
def handle_income(user_id, message, user_data):
    base_user_id = str(user_id).strip()
    retry_tracker = load_json(RETRY_TRACKER_FILE)
    retry_tracker.setdefault(base_user_id, 0)

    # Initialize user structure
    if base_user_id not in user_data:
        user_data[base_user_id] = {"sections": {}, "income": [], "session_info": {}}
    user_data[base_user_id].setdefault("sections", {})
    user_data[base_user_id].setdefault("income", [])
    user_data[base_user_id].setdefault("session_info", {})

    # Initialize pending transaction
    session_info = user_data[base_user_id]["session_info"]
    pending = session_info.setdefault(
        "pending", {"amount": None, "currency": None, "category": None}
    )

    # Only turn add_income ON if no pending transaction exists
    if not any(pending.values()):
        user_data[base_user_id]["sections"]["add_income"] = "on"

    save_json(USER_DATA_FILE, user_data)

    # Extract amount and currency if not already present
    amount, currency = extract_amount_currency(message)
    if amount and not pending["amount"]:
        pending["amount"] = amount
    if currency and not pending["currency"]:
        pending["currency"] = currency
    if not pending["category"]:
        pending["category"] = predict_category(message)

    user_data[base_user_id]["session_info"]["pending"] = pending
    save_json(USER_DATA_FILE, user_data)

    # Check for missing fields
    if not all(pending.values()):
        missing = [k for k, v in pending.items() if not v]
        return f"🤔 I need more information: {', '.join(missing)}."

    # All fields collected → proceed to save
    timestamp = datetime.now().isoformat()
    hash_input = f"{base_user_id}{pending['amount']}{pending['currency']}{pending['category']}{timestamp}"
    record_hash = f"inc{base_user_id}{hashlib.md5(hash_input.encode()).hexdigest()}"

    # AI comment
    comment_prompt = f"""
Write a short human-like remark about this income transaction:
Amount: {pending['currency']} {pending['amount']}
Category: {pending['category']}
Message: {message}
"""
    transaction_comment, err = call_openrouter(comment_prompt)
    if err or not transaction_comment:
        retry_tracker[base_user_id] += 1
        save_json(RETRY_TRACKER_FILE, retry_tracker)
        if retry_tracker[base_user_id] >= 4:
            return f"⚠️ The chat system is down. Please contact admin on WhatsApp (+234 8169482136)."
        transaction_comment = "Income recorded successfully (AI summary unavailable)."
        user_message = "✨ Transaction saved, but AI is offline. Please resend to confirm."
    else:
        retry_tracker[base_user_id] = 0
        save_json(RETRY_TRACKER_FILE, retry_tracker)
        user_message = f"✅ Transaction saved!\nComment: {transaction_comment}"

    # Save transaction to budget.json
    budget = load_json(BUDGET_JSON)
    budget.setdefault("transactions", [])
    record = {
        "id": record_hash,
        "user_id": base_user_id,
        "type": "income",
        "currency": pending["currency"],
        "amount": pending["amount"],
        "category": pending["category"],
        "timestamp": timestamp,
        "comment": transaction_comment,
    }
    budget["transactions"].append(record)
    save_json(BUDGET_JSON, budget)

    # Reset session and turn add_income OFF
    user_data[base_user_id]["sections"]["add_income"] = "off"
    user_data[base_user_id]["session_info"] = {}
    save_json(USER_DATA_FILE, user_data)

    return {"message": user_message, "hash": record_hash}
