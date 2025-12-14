from pyrogram import Client
from config import USERBOT_API_ID, USERBOT_API_HASH, USER_SESSION

user = Client(
    name="user_session",
    api_id=USERBOT_API_ID,
    api_hash=USERBOT_API_HASH,
    session_string=USER_SESSION
)
