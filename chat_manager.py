# chat_manager.py
"""
Central chat manager:
- Routes onboarding/login flows
- Activates channels
- Calls intent_finder.find_intent for registered users
Returns: (response_data, mode, user_id)
where response_data is either:
    - a dict: {"text": "<message text>", "pdf": "<path or None>"}
    - a string (legacy fallback)
"""
from onboarding import handle_onboarding, user_data, save_user_data, start_onboarding
from login_flow import start_login, handle_login
from intent_finder import find_intent
from get_display_name import get_display_name  # should return a displayable name

# Session state tracks if user has been greeted in chat
session_state = {}

def activate_channel(uid, source):
    """Mark this channel as active, others as inactive."""
    for ch in ["whatsapp", "telegram", "web", "local"]:
        user_data[uid].setdefault("channel_state", {})
        user_data[uid]["channel_state"][ch] = (ch == source)
    save_user_data()

def process_message(source="local", source_id=None, text=""):
    """
    Main handler that routes messages between onboarding, login, and chat.
    Returns: (response_data, mode, user_id)
    response_data for chat should be a dict: {"text": str, "pdf": path_or_None}
    """
    user_id = None
    text = text or ""
    # Step 0: Check if user exists for this channel
    if source_id:
        for uid, info in user_data.items():
            if info.get("accounts", {}).get(f"{source}_id") == source_id:
                user_id = uid
                break

    # Step 1: User not found → onboarding/login
    if not user_id:
        text_lower = text.strip().lower()
        if text_lower in ["login", "i have an account", "already registered"]:
            response, done, temp_id = start_onboarding(source, source_id)
            # Immediately set login step
            user_data[temp_id]["step"] = "login_email"
            save_user_data()
            return ({"text": "Okay, let's log you in. Please enter your email address:", "pdf": None}, "login", temp_id)

        # Normal onboarding
        response, done, new_user_id = start_onboarding(source, source_id)
        mode = "chat" if done else "onboarding"
        # If response is string or dict, normalize:
        if isinstance(response, str):
            resp_data = {"text": response, "pdf": None}
        elif isinstance(response, dict):
            # try to map keys to our expected shape
            resp_data = {"text": response.get("text") or response.get("message") or str(response), "pdf": response.get("pdf")}
        else:
            resp_data = {"text": str(response), "pdf": None}
        return (resp_data, mode, new_user_id)

    # Step 2: Activate current channel
    activate_channel(user_id, source)
    step = user_data[user_id].get("step")

    # Step 3: Login flow
    if step in ["login_email", "login_password"]:
        response, done, actual_id = handle_login(user_id, text)
        if done:
            # Mark user as greeted in session
            session_state[actual_id] = {"greeted": True}
            save_user_data()
            return ({"text": f"Welcome back, {get_display_name(actual_id)}! What can I help you with today?", "pdf": None}, "chat", actual_id)
        # response might be instruction string
        if isinstance(response, str):
            return ({"text": response, "pdf": None}, "login", actual_id)
        else:
            return ({"text": str(response), "pdf": None}, "login", actual_id)

    # Step 4: Onboarding flow
    if step != "registered":
        response, done = handle_onboarding(user_id, text)
        if done:
            session_state[user_id] = {"greeted": True}
            save_user_data()
            return ({"text": f"All set, {get_display_name(user_id)}! What can I help you with today?", "pdf": None}, "chat", user_id)
        # return onboarding message
        if isinstance(response, str):
            return ({"text": response, "pdf": None}, "onboarding", user_id)
        else:
            return ({"text": str(response), "pdf": None}, "onboarding", user_id)

    # Step 5: Registered user → greeting if not greeted
    if not session_state.get(user_id, {}).get("greeted"):
        session_state[user_id] = {"greeted": True}
        return ({"text": f"Welcome back, {get_display_name(user_id)}! What can I help you with today?", "pdf": None}, "chat", user_id)

    # Step 6: Normal chat -> use intent finder
    try:
        result = find_intent(user_id, text)
        intent = result.get("intent", "unknown")
        resp = result.get("response", {"summary": "Sorry, I didn’t catch that.", "pdf": None})

        # Normalize response shape
        summary = resp.get("summary") if isinstance(resp, dict) else str(resp)
        pdf = resp.get("pdf") if isinstance(resp, dict) else None

        # Mark this channel as inactive for now (optional)
        user_data[user_id].setdefault("channel_state", {})
        user_data[user_id]["channel_state"][source] = False
        save_user_data()

        # Choose prefix for UI categorization (optional)
        prefix_map = {
            "add_income": "[Income]",
            "add_expense": "[Expense]",
            "set_reminder": "[Reminder]",
            "generate_report": "[Report]",
            "correct_transaction": "[Transaction]"
        }
        prefix = prefix_map.get(intent, "[Chat]")

        text_response = f"{prefix} {summary}"
        return ({"text": text_response, "pdf": pdf}, "chat", user_id)

    except Exception as e:
        # On error, return friendly fallback and log
        return ({"text": f"⚠️ Error processing your message: {e}", "pdf": None}, "chat", user_id)
