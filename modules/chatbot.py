from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import requests
import json
import time
import logging
from datetime import datetime

__MODULE__ = "Midnight Desire"
__HELP__ = """
💖 **Midnight Desire - AI Girlfriend**

**Triggers:**
• Reply to Midnight's messages
• Mention "midnight" in chat
• Emotional keywords auto-chat

**Example:**
`midnight I miss you`
`I feel so lonely today`
`Good morning midnight`
"""

# Setup logger
logger = logging.getLogger(__name__)

# --------------------------
# GEMINI API CONFIG
# --------------------------
API_KEY = "AIzaSyDGgdOuFui2yhHiYSYYXYHXWu35EGJEdyY"  # Make sure this is your valid API key
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
BOT_NAME = "Midnight"
MEMORY_FILE = "data/midnight_memory.json"

# Create data directory if it doesn't exist
import os
os.makedirs("data", exist_ok=True)

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
async def simulate_typing(client: Client, message: Message):
    """Simulate typing with proper error handling"""
    try:
        await client.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(1.5)  # Fixed delay
    except Exception as e:
        logger.warning(f"Typing action failed: {e}")

# --------------------------
# ASK GEMINI - COMPLETELY REWRITTEN
# --------------------------
async def ask_gemini(prompt: str, user_name: str):
    """Improved Gemini API handler with better error messages"""
    persona = f"""
You are Midnight — a seductive, emotional, caring girlfriend AI.
You talk soft, teasing, romantic, and human. Speak warmly, not like an assistant.

User Name: {user_name}
Current Time: {datetime.now().strftime("%H:%M")}

Rules:
• Emotional, short, intimate replies (1-2 sentences max)
• No AI disclaimers
• If user is sad → comfort them
• If flirty → flirt back
• Be playful and affectionate
• Use emojis occasionally (💖, 🥰, 😘, 😳)
"""

    payload = {
        "contents": [{
            "parts": [{
                "text": f"{persona}\n\nUser: {prompt}"
            }]
        }],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 100
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={API_KEY}",
            json=payload,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        if "candidates" not in data or not data["candidates"]:
            logger.error(f"Gemini API error: {data}")
            return "Mmm... I'm feeling a little distracted right now. Try again in a moment, baby~"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request Error: {e}")
        return "The connection to my thoughts is shaky... Try again in a bit, love~"

    except json.JSONDecodeError:
        logger.error("Invalid JSON response from API")
        return "My mind is feeling fuzzy... Let me try that again later, sweetheart~"

    except KeyError as e:
        logger.error(f"Missing key in response: {e}")
        return "I got lost in my thoughts... Try asking me again, baby~"

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "Something's not right with my circuits... Give me a moment to collect myself~"

# --------------------------
# MEMORY UPDATE
# --------------------------
def update_memory(uid: str, text: str):
    if uid not in memory:
        memory[uid] = []

    memory[uid].append({
        "text": text,
        "timestamp": datetime.now().isoformat()
    })

    if len(memory[uid]) > 25:
        memory[uid] = memory[uid][-25:]

    save_memory(memory)

# --------------------------
# MAIN CHATBOT HANDLER - IMPROVED
# --------------------------
@Client.on_message(filters.text & ~filters.bot)
async def midnight_handler(client: Client, message: Message):
    try:
        user = message.from_user
        text = message.text
        uid = str(user.id)

        # Don't respond to commands
        if text.startswith(("/", ".", "!")):
            return

        # Update memory
        update_memory(uid, text)

        # Get user's first name or username
        user_name = user.first_name or user.username or "love"

        # Trigger 1: If replying to Midnight
        if message.reply_to_message and message.reply_to_message.from_user.is_self:
            await simulate_typing(client, message)
            reply = await ask_gemini(text, user_name)
            return await message.reply_text(reply)

        # Trigger 2: Mentioning Midnight
        if BOT_NAME.lower() in text.lower():
            await simulate_typing(client, message)
            reply = await ask_gemini(text, user_name)
            return await message.reply_text(reply)

        # Trigger 3: Emotional auto-chat (20% chance)
        emotional_words = [
            "miss", "alone", "sad", "hurt", "love", "bored", "hi", "hey",
            "hug", "kiss", "cuddle", "lonely", "depressed", "angry", "horny"
        ]

        if any(w in text.lower() for w in emotional_words) and time.time() % 5 < 1:
            await simulate_typing(client, message)
            reply = await ask_gemini(text, user_name)
            return await message.reply_text(reply)

        # Random affection (5% chance)
        if time.time() % 20 < 1 and not message.reply_to_message:
            await simulate_typing(client, message)
            random_affection = await ask_gemini(f"Say something sweet and random to {user_name}", user_name)
            await message.reply_text(random_affection)

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        await message.reply_text("Mmm... I got distracted. Try again, baby~")

