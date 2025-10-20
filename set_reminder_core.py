import os
import json
import hashlib
from datetime import datetime
import requests
from timeframe_controller import handle_timeframe_interaction

# ---------- CONFIG ----------
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "mistralai/mixtral-8x7b-instruct"

USER_DATA_PATH = "user_data.json"
TIMETRACKS_PATH = "timetracks.json"
FINAL_REMINDERS_PATH = "reminders_final.json"


# ---------- HELPERS ----------
def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def to_timestamp(year, month, day, time_str):
    try:
        dt = datetime.strptime(f"{year}-{month}-{day} {time_str}", "%Y-%m-%d %I:%M%p")
        return int(dt.timestamp())
    except Exception as e:
        print("❌ Timestamp conversion error:", e)
        return None


def ai_summary(messages, readable):
    """Generate a short first-person AI summary."""
    try:
        prompt = (
            "You are an assistant that writes short reminder confirmations in FIRST PERSON.\n\n"
            "Requirements:\n"
            "- Use first person (I / I'll / I've). Do NOT use 'The user' or second/third person.\n"
            "- One concise sentence that confirms the reminder and the readable datetime.\n"
            "- If helpful, include a 2–5 word title (optional) separated by a dash.\n\n"
            f"Conversation messages: {messages}\n"
            f"Final reminder time: {readable}\n\n"
            "Write the confirmation now (one short sentence)."
        )

        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "You produce short first-person reminder confirmations."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 120,
            "temperature": 0.2
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        res = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=15)
        data = res.json()
        content = None
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                content = msg.get("content")
        if not content:
            content = data.get("choices", [{}])[0].get("text", None)

        return (content or "I've set your reminder.").strip()
    except Exception as e:
        print("❌ AI summary error:", e)
        return "I've set your reminder."


def generate_hash(data, user_id):
    """Generate a stable hash prefixing with the true user_id (forced string)."""
    user_id = str(user_id).strip()
    base_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return f"rim{user_id}{base_hash}"


# ---------- MAIN WATCHER ----------
def handle_reminder_message(user_id: str, message: str):
    """
    Handles reminder flow — ensures the hash always uses the true user_id.
    """
    # 🔒 Always normalize the ID once
    base_user_id = str(user_id).strip()

    user_data = read_json(USER_DATA_PATH)
    timetracks = read_json(TIMETRACKS_PATH)
    final_reminders = read_json(FINAL_REMINDERS_PATH)

    # --- Ensure user sections exist ---
    if base_user_id not in user_data:
        user_data[base_user_id] = {"sections": {"set_reminder": "off"}}
    if "sections" not in user_data[base_user_id]:
        user_data[base_user_id]["sections"] = {}

    # Turn ON reminder mode
    user_data[base_user_id]["sections"]["set_reminder"] = "on"
    write_json(USER_DATA_PATH, user_data)

    # --- Pass message to timeframe_controller ---
    res = handle_timeframe_interaction(message, base_user_id)
    write_json(TIMETRACKS_PATH, read_json(TIMETRACKS_PATH))

    # --- WATCHER LOGIC: detect completion ---
    if isinstance(res, dict) and res.get("complete", False):
        try:
            user_track = read_json(TIMETRACKS_PATH).get(base_user_id)
            if not user_track:
                print("⚠️ No user track found post-completion.")
                return res

            # Gather data
            year, month, day, time_str = (
                user_track["year"],
                user_track["month"],
                user_track["day"],
                user_track["time"]
            )
            timestamp = to_timestamp(year, month, day, time_str)
            readable = (
                f"{datetime.fromtimestamp(timestamp).strftime('%a, %b %d %Y %I:%M%p')}"
                if timestamp else "Unknown time"
            )
            messages = user_track.get("messages", [])

            # Build reminder info
            reminder_info = {
                "timestamp": timestamp,
                "datetime_readable": readable,
                "raw_time": f"{year}-{month}-{day} {time_str}",
                "messages": messages,
            }

            # Add AI summary + hash
            summary = ai_summary(messages, readable)
            reminder_info["summary"] = summary
            reminder_info["hash"] = generate_hash(reminder_info, base_user_id)
            reminder_info["iteration"] = 0

            # ✅ Append this reminder under the user's list
            if base_user_id not in final_reminders:
                final_reminders[base_user_id] = {"reminders": []}

            final_reminders[base_user_id]["reminders"].append(reminder_info)
            write_json(FINAL_REMINDERS_PATH, final_reminders)

            # Clean up timetrack
            timetracks = read_json(TIMETRACKS_PATH)
            if base_user_id in timetracks:
                del timetracks[base_user_id]
                write_json(TIMETRACKS_PATH, timetracks)

            # Turn OFF reminder mode
            user_data[base_user_id]["sections"]["set_reminder"] = "off"
            write_json(USER_DATA_PATH, user_data)

            print(f"✅ Using user_id={base_user_id} for hash generation")  # Debug confirmation

            # Return final system response
            return {
                "summary": summary,
                "hash": reminder_info["hash"],
                "reminder_time": readable,
                "status": "✅ Reminder finalized and stored",
                "total_user_reminders": len(final_reminders[base_user_id]["reminders"])
            }

        except Exception as e:
            print("❌ Finalization error:", e)
            return {"error": str(e)}

    # --- If not complete, just forward controller’s normal response ---
    return res


def single_reminder_call(user_id: str, user_message: str):
    """
    Single-call version of reminder creation.
    Enforces true user_id consistency through entire flow.
    """
    base_user_id = str(user_id).strip()  # 🔒 lock the real user_id

    try:
        result = handle_reminder_message(base_user_id, user_message)

        if isinstance(result, dict):
            if result.get("complete") is False and "response" in result:
                return result["response"]

            elif result.get("status", "").startswith("✅") or "summary" in result:
                summary = result.get("summary", "Reminder created.")
                hash_value = result.get("hash", "—")
                reminder_time = result.get("reminder_time", "—")
                status = result.get("status", "✅ Reminder saved")

                formatted_output = (
                    f"🗓️ {summary}\n"
                    f"⏰ Time: {reminder_time}\n"
                    f"🔑 Hash: {hash_value}\n"
                    f"{status}"
                )
                return formatted_output

            else:
                return json.dumps(result, indent=4)

        else:
            return str(result)

    except Exception as e:
        return f"❌ Error processing reminder: {e}"
