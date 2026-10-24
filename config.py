import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "").strip()
ADMIN_ID_RAW = (os.getenv("ADMIN_ID") or os.getenv("ADMIN_CHAT_ID") or "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set")
if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is not set")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError as exc:
    raise RuntimeError("ADMIN_ID must be a numeric Telegram user ID") from exc

CREATOR_NAME = "〘Cactuc = نــوید〙"
CREATOR_USERNAME = "cactuc580"
CREATOR_ID_LINK = f"https://t.me/{CREATOR_USERNAME}"
DEFAULT_LANG = "fa"
SUPPORTED_LANGS = ["fa", "en"]
