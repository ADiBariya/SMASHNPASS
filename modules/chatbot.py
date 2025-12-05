
from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import requests
import json
import time

__MODULE__ = "Midnight Desire"
__HELP__ = """
Seductive AI girlfriend with emotions & memory.

**Triggers:**
• Reply to Midnight's messages  
• Mention "midnight" in chat  
• Emotional keywords auto-chat  

Example:
`midnight I miss you`
"""

# --------------------------
# GEMINI API KEY
# --------------------------
API_KEY = "AIzaSyDGgdOuFui2yhHiYSYYXYHXWu35EGJEdyY"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

BOT_NAME = "Midnight"
MEMORY_FILE = "data/midnight_memory.json"


# --------------------------
# MEMORY SYSTEM
# --------------------------
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)


memory = load_memory()


# --------------------------
# TYPING EFFECT
# --------------------------
async def simulate_typing(message: Message, text: str):
    await message.chat.send_chat_action("typing")
    await asyncio.sleep(min(2.5, len(text) * 0.01))


# --------------------------
# ASK GEMINI
# --------------------------
async def ask_gemini(prompt: str, user_name: str):

    persona = f"""
You are Midnight — a seductive, emotional, caring girlfriend AI.
You talk soft, teasing, romantic, and human.
Speak warmly, not like an assistant.

User Name: {user_name}

Rules:
• Emotional, short, intimate replies.
• No AI disclaimers.
• If user is sad → comfort.
• If flirty → flirt back.
"""

    payload = {
        "contents": [
            {"parts": [{"text": persona + "\nUser: " + prompt}]}
        ]
    }

    try:
        response = requests.post(
            GEMINI_URL + f"?key={API_KEY}",
            json=payload
        ).json()

        return response["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Error:", e)
        return "Baby… Midnight is having trouble talking. Try again."


# --------------------------
# MEMORY UPDATE
# --------------------------
def update_memory(uid: str, text: str):
    if uid not in memory:
        memory[uid] = []

    memory[uid].append(text)

    if len(memory[uid]) > 25:
        memory[uid] = memory[uid][-25:]

    save_memory(memory)


# --------------------------
# MAIN CHATBOT HANDLER
# --------------------------
@Client.on_message(filters.text & ~filters.bot)
async def midnight_handler(client, message: Message):

    user = message.from_user
    text = message.text
    uid = str(user.id)

    update_memory(uid, text)

    # Trigger 1: If replying to Midnight
    if message.reply_to_message and message.reply_to_message.from_user.is_self:
        await simulate_typing(message, text)
        reply = await ask_gemini(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 2: Mentioning Midnight
    if BOT_NAME.lower() in text.lower():
        await simulate_typing(message, text)
        reply = await ask_gemini(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 3: Emotional auto-chat
    emotional_words = ["miss", "alone", "sad", "hurt", "love", "bored", "hi", "hey"]
    if any(w in text.lower() for w in emotional_words):
        if time.time() % 10 < 1:
            await simulate_typing(message, text)
            reply = await ask_gemini(text, user.first_name)
            return await message.reply_text(reply)
