# local_chatbot_live.py
from chat_manager import process_message
from get_display_name import get_display_name

# Configure user
USER_ID = "1"
WEB_ID = "web1"

print(f"Local Chat Bot started for user {get_display_name(USER_ID)} (web_id={WEB_ID})")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("Bot: Goodbye!")
        break

    # Send message to chat manager
    response, mode, uid = process_message(source="web", source_id=WEB_ID, text=user_input)
    print(f"Bot [{mode}]: {response}\n")
