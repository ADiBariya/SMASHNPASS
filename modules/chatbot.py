from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import requests
import json
import time

# ----------------------------
# CONFIG
# ----------------------------
AI_API_URL = "https://api.gemini.com/v1/chat"   # Replace with your working API
BOT_NAME = "Midnight"
MEMORY_FILE = "data/midnight_memory.json"

# ----------------------------
# LOAD + SAVE MEMORY
# ----------------------------
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

# ----------------------------
# TYPING EFFECT
# ----------------------------
async def type_effect(msg: Message, text: str):
    await msg.chat.send_chat_action("typing")
    await asyncio.sleep(min(len(text) * 0.01, 3))

# ----------------------------
# ASK AI WITH PERSONALITY
# ----------------------------
async def ask_midnight(prompt: str, username: str):
    personality = f"""
You are Midnight, a seductive, slightly teasing, emotionally warm AI friend.
You talk in a smooth, intimate tone but stay respectful.
You remember details about the user from previous chats.
User name: {username}

Important rules:
1. Speak naturally like a human.
2. Keep responses short and intimate.
3. Never mention you are an AI.
4. Maintain a playful tone.
"""

    full_prompt = personality + "\nUser: " + prompt

    payload = {
        "model": "gemini-pro",
        "input": full_prompt
    }

    try:
        r = requests.post(AI_API_URL, json=payload)
        data = r.json()

        return data.get("response", "I’m here… tell me more.")
    except:
        return "Hmm… something blocked my voice. Try again?"

# ----------------------------
# MEMORY UPDATE
# ----------------------------
def update_memory(user_id: str, text: str):
    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(text)

    if len(memory[user_id]) > 20:
        memory[user_id] = memory[user_id][-20:]

    save_memory(memory)

# ----------------------------
# MAIN CHATBOT HANDLER
# ----------------------------
@Client.on_message(filters.text & ~filters.me & ~filters.bot)
async def midnight_chat(_, message: Message):
    user = message.from_user
    text = message.text
    uid = str(user.id)

    # Save memory
    update_memory(uid, text)

    # Trigger 1: User replies to bot
    if message.reply_to_message and message.reply_to_message.from_user.is_self:
        await type_effect(message, text)
        reply = await ask_midnight(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 2: User says "midnight"
    if BOT_NAME.lower() in text.lower():
        await type_effect(message, text)
        reply = await ask_midnight(text, user.first_name)
        return await message.reply_text(reply)

    # Trigger 3: Auto-chat mode (AI watches chat)
    keywords = ["alone", "bored", "miss", "hey", "hi", "love", "sad"]
    if any(k in text.lower() for k in keywords):
        # 10% chance to auto-chat
        if time.time() % 10 < 1:
            await type_effect(message, text)
            reply = await ask_midnight(text, user.first_name)
            return await message.reply_text(reply)
