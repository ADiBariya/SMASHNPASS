import os

# Bot Configuration - Main credentials
API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Owner Configuration
import os

OWNER_ID = int(os.environ.get("OWNER_ID", "1432702628"))

sudo_default = "1737646273"
SUDO_USERS = ["5869450229", "1737646273", "5162885921"]

# Log Group Configuration
LOG_GROUP_ID = -1003438116493  # Replace with your actual log group chat ID
START_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"  # Your startup image link


# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "smashpassbot")

#Commands
COMMAND_PREFIX = ["!", "/", "."]

#Ma chud jayegi hatya to 
USER_SESSION = ""
USERBOT_API_ID = 
USERBOT_API_HASH = ""

TG_WAIFU_CHANNEL = 

# Bot Settings
BOT_NAME = "WaifuSmash"
BOT_USERNAME = "Waifusmashbot"
OWNER_USERNAME = "https://files.catbox.moe/k23nnw.jpg"

# Game Settings
WIN_CHANCE = 50  # 50% chance to win waifu on smash
DAILY_COINS = 100
SMASH_COST = 10

#Git stuff
GIT_TOKEN = ""
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


