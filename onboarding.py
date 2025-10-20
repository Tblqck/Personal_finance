
import json
import os
import re
import hashlib

USER_DATA_FILE = "user_data.json"

# -------------------- LOAD OR INIT --------------------
if os.path.exists(USER_DATA_FILE):
    try:
        with open(USER_DATA_FILE, "r") as f:
            user_data = json.load(f)
    except json.JSONDecodeError:
        user_data = {}
else:
    user_data = {}


def save_user_data():
    """Save all user data to file."""
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=4)


# -------------------- HELPERS --------------------
def is_valid_email(email):
    """Simple regex email validator."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def next_user_id():
    """Return next available numeric user_id."""
    if not user_data:
        return 1
    return max(int(uid) for uid in user_data.keys()) + 1


def init_sections():
    """Return all sections initialized to off."""
    return {
        "add_expense": "off",
        "add_income": "off",
        "remove_transaction": "off",
        "correct_transaction": "off",
        "set_reminder": "off",
        "remove_reminder": "off",
        "chat": "off"
    }


def init_channel_state():
    """Tracks which channel is active."""
    return {"whatsapp": False, "telegram": False, "web": False}


def find_user_by_channel_id(source, source_id):
    """Return user_id if channel already linked."""
    for uid, info in user_data.items():
        if info.get("accounts", {}).get(f"{source}_id") == source_id:
            return uid
    return None


def find_user_by_email(email):
    """Return user_id if email exists."""
    for uid, info in user_data.items():
        if info.get("email") == email:
            return uid
    return None


# -------------------- ONBOARDING --------------------
def start_onboarding(source=None, source_id=None):
    """
    Start onboarding or reuse existing user if channel already linked.
    """
    # Check if channel (telegram, etc.) already linked
    existing = find_user_by_channel_id(source, source_id) if source_id else None
    if existing:
        user_data[existing]["channel_state"][source] = True
        save_user_data()
        name = user_data[existing].get("name", "User")
        return f"Welcome back, {name}! You’re logged in via {source}.", True, existing

    # Otherwise, create a new user
    new_id = str(next_user_id())
    user_data[new_id] = {
        "step": "awaiting_name",
        "source": source or "local",
        "accounts": {
            "telegram_id": source_id if source == "telegram" else None,
            "whatsapp_id": source_id if source == "whatsapp" else None,
            "web_id": source_id if source == "web" else None
        },
        "channel_state": init_channel_state(),
        "name": None,
        "original_name": None,
        "nickname": None,
        "preferred_name_type": None,
        "email": None,
        "password_hash": None,
        "preferences": [],
        "sections": init_sections(),
        "income": [],
        "expenses": [],
        "session_info": {}
    }
    save_user_data()
    return "Hi! Do you already have an account? (yes/no)", False, new_id


def handle_onboarding(user_id, text):
    """
    Handles onboarding, login, and registration logic.
    """
    user_id = str(user_id)
    step = user_data[user_id].get("step")

    # --- Step 0: Ask login or register ---
    if step == "awaiting_name":  # first step after init
        choice = text.strip().lower()
        if choice in ["yes", "y"]:
            user_data[user_id]["step"] = "awaiting_login_email"
            save_user_data()
            return "Alright! Please enter your registered email:", False
        elif choice in ["no", "n"]:
            user_data[user_id]["step"] = "awaiting_fullname"
            save_user_data()
            return "Okay, let's create one. What’s your full name?", False
        else:
            return "Please reply with 'yes' or 'no'.", False

    # --- Step 1: Full name ---
    if step == "awaiting_fullname":
        user_data[user_id]["name"] = text.upper()
        user_data[user_id]["original_name"] = text
        user_data[user_id]["step"] = "awaiting_nickname"
        save_user_data()
        return f"Nice to meet you, {text}! Do you have a nickname?", False

    # --- Step 2: Nickname ---
    elif step == "awaiting_nickname":
        t = text.strip().lower()
        if t in ["no", "none", "don't have", "nah"]:
            user_data[user_id]["nickname"] = None
            user_data[user_id]["preferred_name_type"] = "name"
            user_data[user_id]["step"] = "awaiting_email"
            save_user_data()
            return "Got it! What's your email address?", False
        else:
            user_data[user_id]["nickname"] = text
            user_data[user_id]["step"] = "awaiting_preference_type"
            save_user_data()
            return "Great! Would you like me to call you by your name or nickname?", False

    # --- Step 3: Preferred name type ---
    elif step == "awaiting_preference_type":
        choice = text.strip().lower()
        if choice not in ["name", "nickname"]:
            return "Please reply with 'name' or 'nickname'.", False
        user_data[user_id]["preferred_name_type"] = choice
        user_data[user_id]["step"] = "awaiting_email"
        save_user_data()
        return "Got it! What's your email address?", False

    # --- Step 4: Email (new registration) ---
    elif step == "awaiting_email":
        if not is_valid_email(text):
            return "That doesn’t look like a valid email. Try again:", False

        existing = find_user_by_email(text)
        if existing:
            user_data[user_id]["step"] = "awaiting_login_password"
            user_data[user_id]["login_target_id"] = existing
            save_user_data()
            return "This email exists. Please enter your password to verify:", False

        user_data[user_id]["email"] = text
        user_data[user_id]["step"] = "awaiting_password"
        save_user_data()
        return "Perfect. Now please choose a password:", False

    # --- Step 5: Login email (existing user) ---
    elif step == "awaiting_login_email":
        if not is_valid_email(text):
            return "That doesn’t look like a valid email. Try again:", False

        existing = find_user_by_email(text)
        if not existing:
            return "No account found with that email. Try again or type 'register' to create one.", False

        user_data[user_id]["login_target_id"] = existing
        user_data[user_id]["step"] = "awaiting_login_password"
        save_user_data()
        return "Please enter your password:", False

    # --- Step 6: Login password ---
    elif step == "awaiting_login_password":
        target = user_data[user_id]["login_target_id"]
        hashed = hashlib.sha256(text.encode()).hexdigest()
        if user_data[target]["password_hash"] == hashed:
            # Merge linked channels
            acc = user_data[user_id]["accounts"]
            for ch, idv in acc.items():
                if idv and not user_data[target]["accounts"].get(ch):
                    user_data[target]["accounts"][ch] = idv
                    user_data[target]["channel_state"][ch.replace("_id", "")] = True

            del user_data[user_id]
            save_user_data()
            return f"Welcome back, {user_data[target]['name']}! You’re now logged in.", True
        else:
            return "Incorrect password. Try again:", False

    # --- Step 7: Registration password ---
    elif step == "awaiting_password":
        hashed = hashlib.sha256(text.encode()).hexdigest()
        user_data[user_id]["password_hash"] = hashed
        user_data[user_id]["step"] = "awaiting_preferences"
        save_user_data()
        return "Password saved securely. What are your interests? (e.g., AI, Tech, Stocks)", False

    # --- Step 8: Preferences ---
    elif step == "awaiting_preferences":
        prefs = [x.strip() for x in text.split(",") if x.strip()]
        user_data[user_id]["preferences"] = prefs
        user_data[user_id]["step"] = "registered"
        save_user_data()
        return f"All set! I’ll remember your preferences: {', '.join(prefs)}.", True

    return "Unexpected step during onboarding.", False
