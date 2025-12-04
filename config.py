# import os
# from dotenv import load_dotenv

# load_dotenv()

# API_ID = int(os.getenv("API_ID", ""))
# API_HASH = os.getenv("API_HASH", "")
# BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://tanog80742_db_user:vvvqLPgNS3tHkhss@cluster0.mfpx8ib.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
# DB_NAME = os.getenv("DB_NAME", "Smashandpass")

# BOT_NAME = os.getenv("BOT_NAME", "Horikita")
# BOT_USERNAME = "Horikita_Robot"
# DATA_DIR = "data"

# SMASH_BASE_CHANCE = float(os.getenv("SMASH_BASE_CHANCE", 0.5))
# COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", 10))

# config.py - Bot Configuration

import os

class Config:
    # Bot Configuration
    API_ID = int(os.environ.get("API_ID", "22733269"))
    API_HASH = os.environ.get("API_HASH", "d1d8331e5b288c572e8bb6baa7d8f833")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "6970989601:AAFYsCo54bL8uphlBsd0qYz69o7JDFehxZg")
    
    # MongoDB Configuration
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://nefer:nefer6080@cluster0.wtfay3u.mongodb.net/?retryWrites=true&w=majority")
    DB_NAME = os.environ.get("DB_NAME", "smashpassbot")
    
    # Bot Settings
    BOT_NAME = "Horikita"
    BOT_USERNAME = "Horikita_Robot"
    OWNER_ID = int(os.environ.get("OWNER_ID", "1432702628"))
    SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", "").split())) if os.environ.get("SUDO_USERS") else []
    
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
    PLUGINS_PATH = "plugins"