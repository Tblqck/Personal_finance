import json
import os
from datetime import datetime
from timeframe_core import extract_time_frame_full

DATA_FILE = "timetracks.json"


# ---------------------- JSON HELPERS ----------------------
def load_json():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------------- MERGE LOGIC ----------------------
def merge_timeframe(old, new):
    """
    Merge new extraction results into the user's ongoing state.

    - Locks any field already confirmed (assumed=False)
    - Updates unresolved ones (assumed=True)
    - Does not overwrite solid data with new assumed values
    """
    merged = old.copy()

    for field in ["year", "month", "day", "time"]:
        flag = f"{field}_assumed"
        old_val, new_val = old.get(field), new.get(field)
        old_assumed, new_assumed = old.get(flag, True), new.get(flag, True)

        # Already confirmed → do not overwrite
        if old_assumed is False:
            continue

        # User reconfirmed same value → lock it
        if old_val == new_val and new_val is not None:
            merged[flag] = False
            merged[field] = new_val
            continue

        # Field resolved by core (assumed=False)
        if old_assumed and not new_assumed:
            merged[field] = new_val
            merged[flag] = False
            continue

        # Still unresolved but value changed → update it
        if new_val is not None and new_val != old_val:
            merged[field] = new_val
            merged[flag] = new_assumed

        # Fill missing values
        if old_val is None and new_val is not None:
            merged[field] = new_val

    # Copy ambiguity flag
    merged["time_ambiguous"] = new.get("time_ambiguous", merged.get("time_ambiguous", False))

    # Merge messages
    merged["messages"] = old.get("messages", []) + new.get("messages", [])
    merged["iteration"] = old.get("iteration", 0) + 1

    # Check if now complete
    unresolved = [
        merged.get("day_assumed", True),
        merged.get("time_assumed", True),
        merged.get("time_ambiguous", False),
    ]
    merged["complete"] = not any(unresolved)

    return merged


# ---------------------- FORMAT SUMMARY ----------------------
def summarize_timeframe(data):
    """
    Build a readable summary (e.g., "Tue, Oct 14 2025 03:00PM") from the stored merged data.
    """
    try:
        if not (data.get("year") and data.get("month") and data.get("day")):
            return "unspecified date"

        date_obj = datetime(
            year=int(data["year"]),
            month=int(data["month"]),
            day=int(data["day"]),
        )

        time_part = data.get("time") or "9:00am"
        return date_obj.strftime(f"%a, %b %d %Y {time_part.upper()}")
    except Exception:
        return "unknown time"


# ---------------------- MAIN CONTROLLER ----------------------
def handle_timeframe_interaction(message, user_id="1"):
    data = load_json()
    user = data.get(user_id, {
        "year": None,
        "month": None,
        "day": None,
        "time": None,
        "iteration": 0,
        "complete": False,
        "year_assumed": True,
        "month_assumed": True,
        "week_assumed": False,
        "day_assumed": True,
        "time_assumed": True,
        "time_ambiguous": False,
        "messages": []
    })

    result = extract_time_frame_full(message)
    if not result:
        response = "I couldn’t extract a valid time from that."
        save_json(data)
        return {"response": response, "user_id": user_id, "complete": user["complete"]}

    core = result[0] if isinstance(result, list) else result

    # Build new state from core
    new_state = {
        "year": None,
        "month": None,
        "day": None,
        "time": None,
        "year_assumed": True,
        "month_assumed": True,
        "week_assumed": True,
        "day_assumed": True,
        "time_assumed": True,
        "time_ambiguous": False,
        "messages": [message]
    }

    try:
        dt = datetime.fromisoformat(core["date"])
        new_state.update({"year": dt.year, "month": dt.month, "day": dt.day})
    except Exception:
        pass

    new_state["time"] = core.get("time")
    for flag in ["year_assumed", "month_assumed", "week_assumed", "day_assumed", "time_assumed", "time_ambiguous"]:
        if flag in core.get("assumptions", {}):
            new_state[flag] = core["assumptions"][flag]

    # Merge intelligently
    merged = merge_timeframe(user, new_state)

    # ---- 🔧 Response built from MERGED, not core ----
    summary_text = summarize_timeframe(merged)

    if merged["complete"]:
        response = f"✅ Reminder set for {summary_text}.\nI’ve locked this in as your final reminder time."
    else:
        ask = []
        if merged["time_ambiguous"]:
            ask.append("Could you confirm the exact time (e.g., 2pm or 2am)?")
        if merged["day_assumed"]:
            ask.append("Which exact day did you mean?")
        response = f"Got it! {summary_text}"
        if ask:
            response += "\nBut I need clarification on:\n- " + "\n- ".join(ask)

    data[user_id] = merged
    save_json(data)

    return {
        "user_id": user_id,
        "iteration": merged["iteration"],
        "complete": merged["complete"],
        "response": response,
        "data_snapshot": merged  # ✅ now mirrors stored data, not just core
    }
