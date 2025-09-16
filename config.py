import os


ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN") or None
USER_BOT_TOKEN=os.getenv("USER_BOT_TOKEN") or None
ADMIN_IDS = os.getenv("ADMIN_IDS") or None   # Replace with your Telegram user ID
USER_BOT_USERNAME = "Piki_Food_bot"
DB_NAME = "foodbot.db"
