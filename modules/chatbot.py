from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import requests
import json
import time

# -------------------------------------
# GEMINI CONFIG
# -------------------------------------
API_KEY = "AIzaSyDGgdOuFui2yhHiYSYYXYHXWu35EGJEdyY"
AI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

BOT_NAME = "Midnight"
MEMORY_FILE = "data/midnight_memory.json"

# -------------------------------------
# LOAD MEMORY
# -------------------------------------
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

# -------------------------------------
# TYPING EFFECT
# -------------------------------------
async def type_effect(message: Message, text: str):
    await message.chat.send_chat_action("typing")
    await asyncio.sleep(min(len(text) * 0.01, 3))

# -------------------------------------
# ASK GEMINI (MAIN AI FUNCTION)
# -------------------------------------
async def ask_midnight(prompt: str, username: str):

    personality = f"""
You are Midnight — a seductive, caring, emotionally warm AI companion.
You tease softly, talk smoothly, and connect deeply.
You talk like a real human, never as an AI.

User name: {username}

Behavior rules:
• Respond short, romantic, playful.
• Never say “as an AI”.
• Show emotions.
• If user is sad, become comforting.
• If user is flirty, become teasing but respectful.
"""

    full_prompt = personality + "\nUser: " + prompt

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            AI_API_URL + f"?key={API_KEY}",
            json=payload
        ).json()

        return response["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Error =", e)
        return "Midnight can't speak right now… try again, darling."

# -------------------------------------
# MEMORY UPDATE
# -------------------------------------
def update_memory(user_id: str, text: str):
    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(text)

    if len(memory[user_id]) > 20:
        memory[user_id] = memory[user_id][-20:]

    save_memory(memory)

# -------------------------------------
# MAIN CHATBOT HANDLER
# -------------------------------------
@Client.on_message(filters.text & ~filters.me & ~filters.bot)
async def midnight_chat(bot, message: Message):

    user = message.from_user
    text = message.text
    uid = str(user.id)

    # Store user message in memory
    update_memory(uid, text)

    # Trigger 1: If replying to Midnight
    if message.reply_to_message and message.reply_to_message.from_user.is_self:
        await type_effect(message, text)
        reply = await ask_midnight(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 2: If user types "midnight"
    if BOT_NAME.lower() in text.lower():
        await type_effect(message, text)
        reply = await ask_midnight(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 3: Auto-Chat (10% chance)
    keywords = ["alone", "bored", "miss", "hi", "hey", "love", "sad", "hurt"]
    if any(k in text.lower() for k in keywords):
        if time.time() % 10 < 1:
            await type_effect(message, text)
            reply = await ask_midnight(text, user.first_name)
            return await message.reply_text(reply)
