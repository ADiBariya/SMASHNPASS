import os

# Bot Configuration - Main credentials
API_ID = int(os.environ.get("API_ID", "22733269"))
API_HASH = os.environ.get("API_HASH", "d1d8331e5b288c572e8bb6baa7d8f833")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "6744296768:AAE_hQJkIkJL7nl91unW2nCidDy0PcYLxH4")

# Owner Configuration
import os

OWNER_ID = int(os.environ.get("OWNER_ID", "1432702628"))

sudo_default = "1737646273"
SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", sudo_default).split()))

# Log Group Configuration
LOG_GROUP_ID = -1003438116493  # Replace with your actual log group chat ID
START_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"  # Your startup image link


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
