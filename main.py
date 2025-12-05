import os
import sys
import asyncio
import importlib
import logging
from pathlib import Path
from datetime import datetime
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from database import db  # mongo connects automatically

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    name="WaifuBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="modules")
)

LOADED_MODULES = {}
HELP_COMMANDS = {}

BOT_START_TIME = datetime.now()

try:
    from config import LOG_GROUP_ID
except ImportError:
    LOG_GROUP_ID = None
    logger.warning("⚠️ LOG_GROUP_ID missing — Logs disabled.")


try:
    from config import SUDO_USERS
except ImportError:
    sudo_default = "1737646273"
    SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", sudo_default).split()))
    logger.info(f"📋 SUDO Users: {SUDO_USERS}")

STARTUP_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"
HELP_IMAGE_URL = "https://i.ibb.co/QjvLFwrP/nari-1.jpg"


# ============================
# MODULE LOADER
# ============================
def load_modules():
    modules_path = Path("modules")
    if not modules_path.exists():
        logger.error("❌ Modules folder not found!")
        return 0, 0

    loaded = 0
    failed = 0

    for file in modules_path.glob("*.py"):
        if file.name.startswith("_"):
            continue

        module_name = file.stem
        try:
            module = importlib.import_module(f"modules.{module_name}")

            LOADED_MODULES[module_name] = {
                "name": getattr(module, "__MODULE__", module_name.title()),
                "help": getattr(module, "__HELP__", "No help available.")
            }

            loaded += 1
            logger.info(f"✅ Loaded module: {module_name}")

        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to load {module_name}: {e}")

    logger.info(f"📦 Modules loaded: {loaded} | Failed: {failed}")
    return loaded, failed


# ============================
# HELP SYSTEM
# ============================
def get_full_help():
    text = "📚 **WAIFU BOT HELP**\n\n"
    for name, info in sorted(LOADED_MODULES.items()):
        text += f"**{info['name']}**\n{info['help']}\n\n"
    return text


# ============================
# STARTUP NOTIFICATION
# ============================
async def send_startup_notification(me, loaded, failed):

    caption = f"""
🚀 **Bot Started Successfully!**

**Bot:** @{me.username}
**Modules:** {loaded} loaded | {failed} failed
**Status:** 🟢 Running

━━━━━━━━━━━━━━
"""

    if LOG_GROUP_ID:
        try:
            await app.send_photo(LOG_GROUP_ID, STARTUP_IMAGE_URL, caption)
        except:
            try:
                await app.send_message(LOG_GROUP_ID, caption)
            except:
                pass

    try:
        await app.send_message(OWNER_ID, caption)
    except:
        pass


# ============================
# SHUTDOWN NOTIFICATION
# ============================
async def send_shutdown_notification(me):
    if not LOG_GROUP_ID:
        return

    uptime = datetime.now() - BOT_START_TIME
    text = f"""
🛑 **Bot Stopped**

**Bot:** @{me.username}
**Uptime:** `{uptime}`
"""

    try:
        await app.send_message(LOG_GROUP_ID, text)
    except:
        pass


# ============================
# START BOT
# ============================
async def start_bot():
    logger.info("🚀 Starting WaifuBot...")

    # MongoDB auto-connects from mongo.py
    logger.info("📡 MongoDB auto-connected")

    loaded, failed = load_modules()

    await app.start()
    me = await app.get_me()
    logger.info(f"🤖 Logged in as @{me.username}")

    await send_startup_notification(me, loaded, failed)

    logger.info("🟢 Bot is now running...")
    await idle()

    await send_shutdown_notification(me)
    await app.stop()
    logger.info("🔴 Bot stopped!")


# ============================
# HELP COMMAND
# ============================
@app.on_message(filters.command(["help"], [".", "/", "!"]))
async def help_handler(client, message):

    # Build inline module menu
    buttons = []
    row = []

    for mod, info in sorted(LOADED_MODULES.items()):
        row.append(InlineKeyboardButton(info["name"], callback_data=f"help_{mod}"))
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("📋 All Commands", callback_data="help_all")])

    caption = """
📚 **Waifu Bot Help**
Select a module to view commands:
"""

    try:
        await message.reply_photo(HELP_IMAGE_URL, caption, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        await message.reply_text(caption, reply_markup=InlineKeyboardMarkup(buttons))


# ============================
# HELP CALLBACK
# ============================
@app.on_callback_query(filters.regex("^help_"))
async def help_callback(client, cb):

    module = cb.data.replace("help_", "")

    if module == "all":
        text = get_full_help()
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "help_back")]]))
        return

    if module == "back":
        await cb.message.edit_text("📚 **Help Menu**", reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(info["name"], callback_data=f"help_{name}")
            ] for name, info in LOADED_MODULES.items()
        ]))
        return

    if module in LOADED_MODULES:
        info = LOADED_MODULES[module]
        await cb.message.edit_text(
            f"📖 **{info['name']}**\n\n{info['help']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "help_back")]])
        )

    await cb.answer()


# ============================
# LOGS COMMAND
# ============================
@app.on_message(filters.command(["logs"], [".", "/", "!"]))
async def logs_handler(client, message):
    if message.from_user.id != OWNER_ID and message.from_user.id not in SUDO_USERS:
        return await message.reply("❌ Access Denied")

    if not os.path.exists("bot.log"):
        return await message.reply("❌ Log file missing!")

    await message.reply_document("bot.log")


# ============================
# RUN BOT
# ============================
if __name__ == "__main__":
    print("🎴 WAIFU SMASH BOT STARTING...")
    try:
        asyncio.get_event_loop().run_until_complete(start_bot())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
