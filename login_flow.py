import hashlib
from onboarding import user_data, save_user_data, find_user_by_email
from get_display_name import get_display_name  # ✅ Correct import

def start_login(user_id):
    """Start login process."""
    user_data[user_id]["step"] = "login_email"
    save_user_data()
    return "Okay! Please enter your email address to log in."

def handle_login(user_id, text):
    """
    Handle login steps, including cross-channel login.
    Returns: (response_text, done_flag, actual_user_id)
    """
    step = user_data[user_id].get("step")

    # Step 1: Ask for email
    if step == "login_email":
        email = text.strip().lower()
        found = find_user_by_email(email)
        if not found:
            return "That email isn’t registered. Would you like to create a new account instead?", False, user_id
        
        # Link temporary user to the existing account
        user_data[user_id]["login_target_id"] = found
        user_data[user_id]["step"] = "login_password"
        save_user_data()
        return "Got it. Now enter your password:", False, user_id

    # Step 2: Verify password
    elif step == "login_password":
        target = user_data[user_id]["login_target_id"]
        hashed = hashlib.sha256(text.encode()).hexdigest()

        if user_data[target]["password_hash"] == hashed:
            # Merge temporary channel info
            temp_acc = user_data[user_id].get("accounts", {})
            for ch, idv in temp_acc.items():
                if idv and not user_data[target]["accounts"].get(ch):
                    user_data[target]["accounts"][ch] = idv
                    user_data[target]["channel_state"][ch.replace("_id", "")] = True

            # Capture display name BEFORE deleting temp user
            display_name = get_display_name(target)

            # Delete temporary user
            del user_data[user_id]
            save_user_data()

            # ✅ Return with the correct user_id (target)
            return f"Welcome back, {display_name}! You’re logged in.", True, target
        else:
            return "Incorrect password. Please try again:", False, user_id

    # Unknown step fallback
    else:
        return "Oops! Something went wrong with your login. Please start again.", False, user_id
