from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import json

# Optional: Use DB if needed
# from database.mongo import db

API_URL = "https://api.gemini.com/v1/chat"   # example placeholder
BOT_NAME = "Midnight"

async def ask_ai(question: str):
    # NOTE: Replace this with your API endpoint or logic
    payload = {
        "model": "gemini-pro",
        "input": question
    }

    try:
        result = requests.post(API_URL, json=payload)
        data = result.json()
        return data.get("response", "I couldn't understand.")
    except:
        return "AI service not reachable right now."

@Client.on_message(filters.text & ~filters.me & ~filters.bot)
async def chatbot(_, message: Message):
    text = message.text

    # Ignore commands from Midnight Desire
    if text.startswith("/"):
        return

    # Your chatbot activation trigger
    if message.reply_to_message and message.reply_to_message.from_user.is_self:
        reply = await ask_ai(text)
        return await message.reply_text(reply)

    # Auto-chat mode (optional)
    if "midnight" in text.lower():
        reply = await ask_ai(text)
        return await message.reply_text(reply)
