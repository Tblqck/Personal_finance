import json
import os

# Path to your user data file
USERDATA_FILE = "user_data.json"  # ✅ Change this if your file is in a different path


def get_display_name(user_id: str) -> str:
    """
    Fetch preferred user name or nickname from userdata.json.
    Prints debug info for clarity.
    """
    if not os.path.exists(USERDATA_FILE):
        print(f"[DEBUG] userdata.json not found — defaulting to 'User {user_id}'")
        return f"User {user_id}"

    try:
        with open(USERDATA_FILE, "r") as f:
            data = json.load(f)

        print("[DEBUG] Loaded user_data.json successfully ✅")

        info = data.get(str(user_id))
        if not info:
            print(f"[DEBUG] No entry found for user_id={user_id}")
            return f"User {user_id}"

        preferred = info.get("preferred_name_type", "name")
        display_name = (
            info.get(preferred)
            or info.get("name")
            or info.get("nickname")
            or f"User {user_id}"
        )

        print(f"[DEBUG] ✅ Display name for user_id={user_id}: {display_name}")
        return display_name

    except Exception as e:
        print(f"[DEBUG] ⚠️ Error reading userdata.json: {e}")
        return f"User {user_id}"


# === Test directly from terminal ===
if __name__ == "__main__":
    import sys

    # You can call it like:  python get_display_name.py 1
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = "1"

    name = get_display_name(user_id)
    print(f"\nFinal Display name for user {user_id}: {name}")
