# auth.py
import hashlib
from onboarding import user_data, save_user_data

def verify_password(stored_hash, password):
    return stored_hash == hashlib.sha256(password.encode()).hexdigest()

def handle_login(user_id, text):
    """
    Login flow by name -> email -> password
    """
    user_id = str(user_id)
    step = user_data[user_id].get("step")

    if step == "login_name":
        # Normalize for case-insensitive name match
        name_input = text.strip().upper()
        match = None
        for uid, u in user_data.items():
            if u.get("name", "").upper() == name_input:
                match = uid
                break
        if match:
            user_data[user_id]["match_id"] = match
            user_data[user_id]["step"] = "login_email"
            save_user_data()
            return f"Hi {text}, please provide your email to continue.", False
        return "Name not found. Try again:", False

    elif step == "login_email":
        match_id = user_data[user_id]["match_id"]
        if user_data[match_id]["email"].lower() == text.lower():
            user_data[user_id]["step"] = "login_password"
            save_user_data()
            return "Email confirmed. Please enter your password:", False
        return "Email does not match. Try again:", False

    elif step == "login_password":
        match_id = user_data[user_id]["match_id"]
        if verify_password(user_data[match_id]["password"], text):
            user_data[user_id] = user_data[match_id]
            user_data[user_id]["step"] = "registered"
            save_user_data()
            return "Login successful! Welcome back.", True
        return "Incorrect password. Try again:", False

    return "Unexpected step in login.", False
