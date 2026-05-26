import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_KEY = os.getenv("TELEGRAM_KEY")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

print(f"Loaded TELEGRAM_KEY: {'set' if TELEGRAM_KEY else 'NOT SET'}"
      f" and MY_CHAT_ID: {MY_CHAT_ID}"
      )
