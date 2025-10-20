import sys
def main(user_id, user_message):
    return f"Reminder removed for {user_id}: '{user_message}'"
if __name__ == "__main__":
    user_id = sys.argv[1]
    user_message = " ".join(sys.argv[2:])
    print(main(user_id, user_message))
