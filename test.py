# test_income.py
import json
from income_core import handle_income, load_json, USER_DATA_FILE, BUDGET_JSON

# ------------------- Test Config -------------------
TEST_USER_ID = "1"
TEST_MESSAGES = [
    "I earned 5000 naira from freelance work"
]

def run_income_tests():
    # Load or initialize user data
    user_data = load_json(USER_DATA_FILE)
    user_data.setdefault(TEST_USER_ID, {"sections": {}, "income": [], "expenses": [], "session_info": {}})

    for msg in TEST_MESSAGES:
        response = handle_income(TEST_USER_ID, msg, user_data)
        print(f"Message: {msg}")
        print("Response:", response)
        print("-" * 40)

if __name__ == "__main__":
    run_income_tests()
