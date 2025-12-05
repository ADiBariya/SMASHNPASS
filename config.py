import os

# Bot Configuration - Main credentials
API_ID = int(os.environ.get("API_ID", "22733269"))
API_HASH = os.environ.get("API_HASH", "d1d8331e5b288c572e8bb6baa7d8f833")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "6970989601:AAFYsCo54bL8uphlBsd0qYz69o7JDFehxZg")

# Owner Configuration
OWNER_ID = int(os.environ.get("OWNER_ID", "1432702628"))
SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", "1737646273").split())) if os.environ.get("SUDO_USERS") else []

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://nefer:nefer6080@cluster0.wtfay3u.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DB_NAME", "smashpassbot")

#Commands
COMMAND_PREFIX = ["!", "/", "."]

# Bot Settings
BOT_NAME = "Horikita"
BOT_USERNAME = "Horikita_Robot"

# Game Settings
WIN_CHANCE = 50  # 50% chance to win waifu on smash
DAILY_COINS = 100
SMASH_COST = 10

# Rarity Multipliers
RARITY_POINTS = {
    "common": 10,
    "rare": 25,
    "epic": 50,
    "legendary": 100,
    "mythic": 250
}

# Plugins Path
PLUGINS_PATH = "modules"  # Changed from "plugins" to match your main.py
