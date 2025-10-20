
import json
import os
import time
from datetime import datetime, timezone
import requests
from config import TELEGRAM_TOKEN  # ✅ Import directly from config.py

# ---------------- CONFIG ----------------
USER_DATA_FILE = "user_data.json"
REMINDER_FILE = "reminders_final.json"

# Time thresholds in hours for reminders
REMINDER_STAGES = [48, 24, 12, 2]


# ---------------- UTILITIES ----------------
def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def send_telegram_message(chat_id, text):
    """Send message to Telegram user."""
    if not TELEGRAM_TOKEN:
        print("[!] TELEGRAM_TOKEN not set in config.py. Message not sent.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print(f"[TG ✅] Sent to {chat_id}: {text}")
            return True
        else:
            print(f"[TG ❌] Failed ({r.status_code}): {r.text}")
            return False
    except Exception as e:
        print(f"[TG ERROR] {e}")
        return False


def send_whatsapp_message(whatsapp_id, text):
    """Placeholder for WhatsApp integration (Twilio, etc.)."""
    if not whatsapp_id:
        return
    print(f"[WA 💬] Would send to {whatsapp_id}: {text}")
    # TODO: Implement Twilio or WhatsApp API integration here


# ---------------- MAIN EXECUTION ----------------
def execute_reminders():
    """Check all reminders and send alerts based on time proximity."""
    now = int(datetime.now(timezone.utc).timestamp())

    reminders_data = load_json(REMINDER_FILE)
    user_data = load_json(USER_DATA_FILE)

    updated = False

    for user_id, reminder_info in reminders_data.items():
        user_reminders = reminder_info.get("reminders", [])
        if not user_reminders:
            continue

        # Get Telegram/WhatsApp IDs
        user_accounts = user_data.get(user_id, {}).get("accounts", {})
        telegram_id = user_accounts.get("telegram_id")
        whatsapp_id = user_accounts.get("whatsapp_id")

        for reminder in user_reminders:
            timestamp = reminder.get("timestamp")
            summary = reminder.get("summary", "Upcoming event reminder!")
            iteration = reminder.get("iteration", 0)

            if not timestamp:
                continue

            time_diff_hours = (timestamp - now) / 3600

            # Check each stage threshold
            if iteration < len(REMINDER_STAGES):
                next_stage = REMINDER_STAGES[iteration]
                if next_stage - 0.2 <= time_diff_hours <= next_stage + 0.2:
                    msg = f"⏰ Reminder: {summary}\n({int(time_diff_hours)} hours left)"
                    if telegram_id:
                        send_telegram_message(telegram_id, msg)
                    if whatsapp_id:
                        send_whatsapp_message(whatsapp_id, msg)
                    reminder["iteration"] += 1
                    updated = True

            # Cleanup: if event time has passed
            elif timestamp < now and iteration < 5:
                msg = f"✅ Reminder Complete: {summary}"
                if telegram_id:
                    send_telegram_message(telegram_id, msg)
                if whatsapp_id:
                    send_whatsapp_message(whatsapp_id, msg)
                reminder["iteration"] = 5
                updated = True

    # Save updated reminders
    if updated:
        save_json(REMINDER_FILE, reminders_data)
        print("[💾] Reminders updated.")


# ---------------- LOOP EXECUTOR ----------------
if __name__ == "__main__":
    print("🚀 Reminder execution service started.")
    while True:
        execute_reminders()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sleeping 5 minutes...")
        time.sleep(300)
