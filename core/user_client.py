# core/user_client.py
from pyrogram import Client
from config import API_ID, API_HASH, USER_SESSION

user = Client(
    name="user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=USER_SESSION
)
