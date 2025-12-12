import os

# Bot Configuration - Main credentials
API_ID = int(os.environ.get("API_ID", "22733269"))
API_HASH = os.environ.get("API_HASH", "d1d8331e5b288c572e8bb6baa7d8f833")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7890556580:AAEZc-D0md92nvKqk80n8EC6awmq9OlQ424")

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

#Ma chud jayegi hatya to 
USER_SESSION = "BQGMv38AGjmk7s_QraPH1WBvhUqLx5B6I7jwMG3Uj2jtoM4u1JlWTyKMtVnS56SkI1iLwc6moDCqc2LkcNwGo_9fPSbQEs2lFiiMQgJEfMNZ99DmRFrKjyRYPiHEDKDi-tpE2g4LkM5LmYnptR8SvyCJHlHSIHqVUI0mNznw-jLGgRL7cdY6WNYhZVkWolG0OCZtEot2X5Hxh4nebfBK16hpEmbzNMVV70XUp7ahNFbD3lzE2SKeUh4wacQnkD8mb7T5rBW2afOA_rp-5-voVo7H5gBliRCdZiYVUJMj2HoY8Yui78WEoIw01NY_LSvv8KuK7izvf0CrhCKguTRrWWdZp2ryfAAAAAHU_2psAA"
USERBOT_API_ID = 26001279
USERBOT_API_HASH = "78f002fc6769c951880b0938e498936a"

TG_WAIFU_CHANNEL = -1003322377810

# Bot Settings
BOT_NAME = "WaifuSmash"
BOT_USERNAME = "Waifusmashbot"
OWNER_USERNAME = "https://files.catbox.moe/k23nnw.jpg"

# Game Settings
WIN_CHANCE = 50  # 50% chance to win waifu on smash
DAILY_COINS = 100
SMASH_COST = 10

#Git stuff
GIT_TOKEN = "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"
GIT_REPO = "https://github.com/ADiBariya/SMASHNPASS"
GIT_BRANCH = "main"

# Channels/Groups
UPDATES_CHANNEL = "WaifusmashUpdates"  # Without @
SUPPORT_GROUP = "WaifusmashSupport"  # Without @
# Rarity Multipliers


RARITY_POINTS = {
        "common": 500,
        "epic": 1500,
        "legendary": 3000,
        "rare": 5000
    }

# Plugins Path
PLUGINS_PATH = "modules"  # Changed from "plugins" to match your main.py


