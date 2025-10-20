# budget_core.py
import sys
import json

def news_handler(user_id, user_message):
    # extend with DB logic, expense tracking, etc.
    return {
        "status": "ok",
        "user_id": user_id,
        "message_received": user_message,
        "response": f"Recorded expense for user {user_id}: {user_message}"
    }

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        user_message = " ".join(sys.argv[2:])
    else:
        user_id = "unknown"
        user_message = ""

    reply = news_handler(user_id, user_message)
    # Print JSON so caller can parse easily
    print(json.dumps(reply))
