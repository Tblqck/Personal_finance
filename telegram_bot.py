# ---------------- TELEGRAM BOT (Full Fixed Version) ----------------
import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- IMPORTS ----------------
from intent_finder import find_intent  # local intent router
from config import TELEGRAM_TOKEN  # bot token from config file

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


# ---------------- COMMAND HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    user_id = str(update.message.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    # Initialize user data if not already present
    user_data.setdefault(user_id, {
        "sections": {},
        "income": [],
        "expenses": [],
        "session_info": {}
    })
    save_json(USER_DATA_FILE, user_data)

    welcome_text = (
        f"👋 Hi {update.message.from_user.first_name or 'there'}!\n"
        "I'm your personal finance assistant.\n\n"
        "You can say things like:\n"
        "• I earned ₦5000 today\n"
        "• I spent ₦200 on food\n"
        "• Remind me to pay rent on Monday\n"
        "• Show me my last month report\n\n"
        "Let's get started!"
    )
    await update.message.reply_text(welcome_text)


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for normal text messages."""
    user_id = str(update.message.from_user.id)
    message = update.message.text.strip()

    try:
        # Step 1 — Detect intent and process
        result = find_intent(user_id, message)

        # Step 2 — Extract data
        intent = result.get("intent")
        response_data = result.get("response", {})

        # Step 3 — Decide reply text
        if isinstance(response_data, dict):
            reply_text = (
                response_data.get("message")
                or response_data.get("summary")
                or json.dumps(response_data, indent=2)
            )
        else:
            reply_text = str(response_data)

        # Step 4 — If there’s a PDF, send it
        pdf_path = None
        if isinstance(response_data, dict):
            pdf_path = response_data.get("pdf")

        if pdf_path and isinstance(pdf_path, str) and os.path.exists(pdf_path):
            await update.message.reply_document(open(pdf_path, "rb"), caption=reply_text)
        else:
            await update.message.reply_text(reply_text)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Something went wrong: {str(e)}")
        print(f"❌ Error handling message: {e}")


# ---------------- MAIN ENTRY POINT ----------------
def main():
    """Start the Telegram bot."""
    print("🚀 Telegram bot starting...")

    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ TELEGRAM_TOKEN is missing in config.py!")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
