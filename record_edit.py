import json
import os
from datetime import datetime

# ------------- CONFIG -------------
USER_FILE = "user_data.json"
BUDGET_FILE = "budget.json"
REMINDER_FILE = "reminders_final.json"

CATEGORIES = ["salary", "bonus", "investment", "gift", "other"]
CURRENCIES = ["USD", "NGN", "EUR", "GBP"]

# ------------- HELPERS -------------

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def update_user_section_flag(user_id, flag_name, state):
    users = load_json(USER_FILE)
    if str(user_id) not in users:
        return
    users[str(user_id)]["sections"][flag_name] = state
    save_json(USER_FILE, users)

# ------------- MAIN HANDLER -------------

def handle_record_edit(user_id, action, record_hash, new_data=None):
    """
    Edit or delete a record for a user.

    Parameters:
    - user_id: str or int
    - action: "edit" or "delete"
    - record_hash: str
    - new_data: dict (required for edit, ignored for delete)
      For income/expense:
          {"currency": "NGN", "amount": 12000, "category": "salary"}
      For reminder:
          {"year": 2025, "month": 10, "day": 20, "time": "14:30", "summary": "task"}
    """

    # Turn on correct_transaction flag
    update_user_section_flag(user_id, "correct_transaction", "on")

    # Determine file & key based on hash prefix
    prefix = record_hash[:3]
    if prefix in ["inc", "exp"]:
        data_file = BUDGET_FILE
        key = "income" if prefix == "inc" else "expenses"
        data_type = "Income" if prefix == "inc" else "Expense"
    elif prefix == "rim":
        data_file = REMINDER_FILE
        key = "reminders"
        data_type = "Reminder"
    else:
        update_user_section_flag(user_id, "correct_transaction", "off")
        return "❌ Invalid record type."

    data = load_json(data_file)
    user_records = data.get(str(user_id), {}).get(key, [])

    # Find the record by hash
    record = next((r for r in user_records if r.get("hash") == record_hash), None)
    if not record:
        update_user_section_flag(user_id, "correct_transaction", "off")
        return f"⚠️ No {data_type.lower()} found with that ID."

    # ----- DELETE -----
    if action == "delete":
        user_records.remove(record)
        save_json(data_file, data)
        update_user_section_flag(user_id, "correct_transaction", "off")
        return f"🗑️ {data_type} record deleted successfully."

    # ----- EDIT -----
    if action == "edit":
        if new_data is None:
            update_user_section_flag(user_id, "correct_transaction", "off")
            return "⚠️ No new data provided for editing."

        try:
            if prefix in ["inc", "exp"]:
                currency = new_data.get("currency")
                amount = float(new_data.get("amount", 0))
                category = new_data.get("category")
                if currency not in CURRENCIES or category not in CATEGORIES:
                    update_user_section_flag(user_id, "correct_transaction", "off")
                    return "⚠️ Invalid currency or category."

                record.update({
                    "currency": currency,
                    "amount": amount,
                    "category": category,
                    "timestamp": datetime.now().timestamp(),
                    "datetime_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            elif prefix == "rim":
                year = int(new_data.get("year"))
                month = int(new_data.get("month"))
                day = int(new_data.get("day"))
                time_str = new_data.get("time")
                summary = new_data.get("summary")
                timestamp = datetime.strptime(f"{year}-{month}-{day} {time_str}", "%Y-%m-%d %H:%M").timestamp()

                record.update({
                    "year": year,
                    "month": month,
                    "day": day,
                    "time": time_str,
                    "summary": summary,
                    "timestamp": timestamp,
                    "datetime_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            save_json(data_file, data)
            update_user_section_flag(user_id, "correct_transaction", "off")
            return f"✅ {data_type} record updated successfully!"

        except Exception as e:
            update_user_section_flag(user_id, "correct_transaction", "off")
            return f"❌ Failed to edit {data_type.lower()}: {str(e)}"

    update_user_section_flag(user_id, "correct_transaction", "off")
    return "❌ Unknown action."
