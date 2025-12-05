from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import requests
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

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
API_KEY = "AIzaSyDnB2UT0lIEz-IMcoVQZjAme6TKsAKlRVc"  # Make sure this is your valid API key
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
BOT_NAME = "Midnight"
MEMORY_FILE = "data/midnight_memory.json"

# Create data directory if it doesn't exist
import os
os.makedirs("data", exist_ok=True)

# --------------------------
# MEMORY SYSTEM
# --------------------------
def load_memory() -> Dict[str, Any]:
    """Load memory from file with error handling"""
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_memory(memory: Dict[str, Any]) -> None:
    """Save memory to file with error handling"""
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")

memory = load_memory()

# --------------------------
# TYPING EFFECT - FIXED
# --------------------------
async def simulate_typing(client: Client, message: Message) -> None:
    """Simulate typing with proper error handling"""
    try:
        if hasattr(message, 'chat') and hasattr(message.chat, 'id'):
            await client.send_chat_action(message.chat.id, "typing")
            await asyncio.sleep(1.5)  # Fixed delay
    except Exception as e:
        logger.warning(f"Typing action failed: {e}")

# --------------------------
# ASK GEMINI - COMPLETELY REWRITTEN
# --------------------------
async def ask_gemini(prompt: str, user_name: str) -> str:
    """Improved Gemini API handler with comprehensive error handling"""
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
        # First check if API key is valid
        if not API_KEY or len(API_KEY) < 30:
            logger.error("Invalid API key")
            return "Mmm... I'm feeling a bit sleepy right now. Try again later, baby~"

        response = requests.post(
            f"{GEMINI_URL}?key={API_KEY}",
            json=payload,
            headers=headers,
            timeout=15
        )

        # Check for HTTP errors
        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {response.text}")
            return "My thoughts are feeling jumbled... Try again, love~"

        # Check for API errors
        if "error" in data:
            logger.error(f"Gemini API error: {data['error']}")
            return "I'm having trouble focusing... Try again soon, baby~"

        # Check for candidates
        if "candidates" not in data or not data["candidates"]:
            logger.error(f"No candidates in response: {data}")
            return "I got distracted... Let me try that again, sweetheart~"

        # Check for content parts
        if not data["candidates"][0].get("content") or not data["candidates"][0]["content"].get("parts"):
            logger.error(f"No content parts: {data}")
            return "My mind wandered off... Try again, love~"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request Error: {e}")
        return "The connection to my thoughts is shaky... Try again in a bit, love~"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "Something's not right with my circuits... Give me a moment to collect myself~"

# --------------------------
# MEMORY UPDATE - IMPROVED
# --------------------------
def update_memory(uid: str, text: str) -> None:
    """Update memory with timestamp and better structure"""
    if uid not in memory:
        memory[uid] = []

    memory[uid].append({
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "type": "user"
    })

    if len(memory[uid]) > 25:
        memory[uid] = memory[uid][-25:]

    save_memory(memory)

# --------------------------
# MAIN CHATBOT HANDLER - COMPLETELY REWRITTEN
# --------------------------
@Client.on_message(filters.text & ~filters.bot)
async def midnight_handler(client: Client, message: Message):
    """Main handler with comprehensive error handling"""
    try:
        # Skip commands and empty messages
        if not message.text or message.text.startswith(("/", ".", "!")):
            return

        user = message.from_user
        text = message.text
        uid = str(user.id)
        user_name = user.first_name or user.username or "love"

        # Update memory
        update_memory(uid, text)

        # Get context from memory
        context = "\n".join([f"{msg['timestamp']}: {msg['text']}" for msg in memory.get(uid, [])[-3:]])

        # Trigger 1: If replying to Midnight
        if message.reply_to_message and message.reply_to_message.from_user.is_self:
            await simulate_typing(client, message)
            reply = await ask_gemini(f"Context: {context}\n\n{text}", user_name)
            return await message.reply_text(reply)

        # Trigger 2: Mentioning Midnight
        if BOT_NAME.lower() in text.lower():
            await simulate_typing(client, message)
            reply = await ask_gemini(f"Context: {context}\n\n{text}", user_name)
            return await message.reply_text(reply)

        # Trigger 3: Emotional auto-chat (20% chance)
        emotional_words = [
            "miss", "alone", "sad", "hurt", "love", "bored", "hi", "hey",
            "hug", "kiss", "cuddle", "lonely", "depressed", "angry", "horny",
            "goodnight", "good morning", "goodnight", "morning", "night"
        ]

        if any(w in text.lower() for w in emotional_words) and time.time() % 5 < 1:
            await simulate_typing(client, message)
            reply = await ask_gemini(f"Context: {context}\n\n{text}", user_name)
            return await message.reply_text(reply)

    except Exception as e:
        logger.error(f"Chatbot error: {e}", exc_info=True)
        await message.reply_text("Mmm... I got distracted. Try again, baby~")
