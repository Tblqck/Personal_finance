# requirements.py
# -----------------------------
# Installs all dependencies for Telegram + WhatsApp bot
# and sets ngrok auth token.
# Run this once before starting your bot.

import os
import subprocess
import sys

# -----------------------------
# Python Packages to Install
# -----------------------------
packages = [
    "python-telegram-bot==21.7",
    "nest_asyncio",
    "dateparser",
    "flask",
    "flask-ngrok",
    "pyngrok",
    "requests",
    "pytz",
    "PyPDF2",
    "twilio"  # <-- Added for WhatsApp bot
]

print("🚀 Installing Python packages...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir"] + packages)

# -----------------------------
# Ngrok Auth Token Setup
# -----------------------------
NGROK_AUTHTOKEN = "34CW8DpM5rg3Kx8iX3oC5tOgn2i_227CJvK8Ah7G5bdrwAbPm"

print("🔑 Setting up ngrok auth token...")
subprocess.run(["ngrok", "config", "add-authtoken", NGROK_AUTHTOKEN])

print("✅ Setup complete. You can now run your Telegram + WhatsApp bot.")
