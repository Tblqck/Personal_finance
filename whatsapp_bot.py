# ---------------- WHATSAPP BOT (Auto Flask + Ngrok) ----------------
import os
import json
import threading
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pyngrok import ngrok

# ---------------- IMPORTS ----------------
from intent_finder import find_intent  # reuse your Telegram intent system
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

# ---------------- FILE PATHS ----------------
USER_DATA_FILE = "user_data.json"

# ---------------- UTILITIES ----------------
def load_json(file_path):
    """Load JSON safely, returning empty dict on failure."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(file_path, data):
    """Save JSON safely."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- FLASK APP ----------------
app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    incoming_msg = request.values.get("Body", "").strip()
    user_number = request.values.get("From")  # e.g. whatsapp:+123456789

    user_data = load_json(USER_DATA_FILE)
    user_data.setdefault(user_number, {
        "sections": {},
        "income": [],
        "expenses": [],
        "session_info": {}
    })
    save_json(USER_DATA_FILE, user_data)

    resp = MessagingResponse()

    try:
        result = find_intent(user_number, incoming_msg)
        response_data = result.get("response", {})

        if isinstance(response_data, dict):
            reply_text = (
                response_data.get("message")
                or response_data.get("summary")
                or json.dumps(response_data, indent=2)
            )
        else:
            reply_text = str(response_data)

        pdf_path = None
        if isinstance(response_data, dict):
            pdf_path = response_data.get("pdf")

        if pdf_path and os.path.exists(pdf_path):
            reply_text += f"\n\n📄 PDF: {pdf_path}"
        resp.message(reply_text)

    except Exception as e:
        resp.message(f"⚠️ Error: {str(e)}")
        print(f"❌ Error handling message: {e}")

    return str(resp)

# ---------------- STARTUP ----------------
def start_flask():
    """Start Flask app."""
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Step 1 — Create public ngrok tunnel
    public_url = ngrok.connect(5000).public_url
    webhook_url = f"{public_url}/whatsapp"

    # Step 2 — Print the webhook to register in Twilio
    print("🚀 WhatsApp bot running!")
    print(f"🌍 Public URL: {public_url}")
    print(f"🔗 Your Webhook URL (use in Twilio): {webhook_url}")

    # Step 3 — Start Flask in background
    threading.Thread(target=start_flask).start()
