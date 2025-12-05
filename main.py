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
from database import db

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

# Store loaded modules info
LOADED_MODULES = {}
HELP_COMMANDS = {}

# Bot start time for uptime tracking
BOT_START_TIME = datetime.now()

# --------------------------
# LOG GROUP & STARTUP IMAGE
# --------------------------
try:
    from config import LOG_GROUP_ID
except ImportError:
    LOG_GROUP_ID = None
    logger.warning("⚠️ LOG_GROUP_ID not found in config. Log notifications disabled.")

# --------------------------
# SUDO USERS CONFIGURATION
# --------------------------
try:
    from config import SUDO_USERS
except ImportError:
    sudo_default = "1737646273"
    SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", sudo_default).split()))
    logger.info(f"📋 SUDO Users: {SUDO_USERS}")

# Startup and Help image URL (same image)
STARTUP_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"
HELP_IMAGE_URL = "https://i.ibb.co/QjvLFwrP/nari-1.jpg"  


def load_modules():
    """Load all modules from modules folder"""
    modules_path = Path("modules")
    
    if not modules_path.exists():
        logger.error("Modules folder not found!")
        return 0, 0
    
    loaded = 0
    failed = 0
    
    for file in modules_path.glob("*.py"):
        if file.name.startswith("_"):
            continue
        
        module_name = file.stem
        
        try:
            module = importlib.import_module(f"modules.{module_name}")
            
            # Store module info
            LOADED_MODULES[module_name] = {
                "name": getattr(module, "__MODULE__", module_name.title()),
                "help": getattr(module, "__HELP__", "No help available.")
            }
            
            loaded += 1
            logger.info(f"✅ Loaded: {module_name}")
            
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to load {module_name}: {e}")
    
    logger.info(f"📦 Modules: {loaded} loaded, {failed} failed")
    return loaded, failed


def get_full_help():
    """Generate full help text"""
    help_text = "📚 **WAIFU BOT HELP**\n\n"
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        help_text += f"**{info['name']}**\n"
        help_text += f"{info['help']}\n\n"
    
    return help_text


def get_module_list():
    """Get list of loaded modules"""
    text = "📦 **Loaded Modules**\n\n"
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        text += f"• **{info['name']}** (`{module_name}`)\n"
    
    text += f"\n📊 Total: {len(LOADED_MODULES)} modules"
    return text


async def send_startup_notification(me, loaded_count, failed_count):
    """Send startup notification to log group and owner"""
    startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    caption = f"""
🚀 **Bot Started Successfully!**

**Bot Information:**
├ **Username:** @{me.username}
├ **Bot ID:** `{me.id}`
├ **Name:** {me.first_name}
└ **Started:** `{startup_time}`

**Module Status:**
├ ✅ **Loaded:** {loaded_count}
├ ❌ **Failed:** {failed_count}
└ 📊 **Total:** {loaded_count + failed_count}

**System Status:**
├ 🗄️ **Database:** Connected
├ 🔧 **Plugins:** Active
└ 🟢 **Status:** Online

━━━━━━━━━━━━━━━━━━━━
⏰ Bot is now running!
    """
    
    # Send to log group
    if LOG_GROUP_ID:
        try:
            logger.info(f"📤 Sending startup notification to log group: {LOG_GROUP_ID}")
            await app.send_photo(
                chat_id=LOG_GROUP_ID,
                photo=STARTUP_IMAGE_URL,
                caption=caption
            )
            logger.info("✅ Startup notification sent to log group!")
        except Exception as e:
            logger.error(f"❌ Failed to send to log group: {e}")
            # Fallback to text message
            try:
                await app.send_message(
                    chat_id=LOG_GROUP_ID,
                    text=caption + "\n\n⚠️ _Image failed to load_"
                )
                logger.info("✅ Startup notification sent (text fallback)")
            except Exception as e2:
                logger.error(f"❌ Failed to send text fallback: {e2}")
    
    # Send to owner
    try:
        logger.info(f"📤 Sending startup notification to owner: {OWNER_ID}")
        await app.send_message(
            OWNER_ID,
            f"✅ **Bot Started!**\n\n"
            f"**Bot:** @{me.username}\n"
            f"**Modules:** {loaded_count} loaded, {failed_count} failed\n"
            f"**Status:** 🟢 Online\n"
            f"**Time:** `{startup_time}`"
        )
        logger.info("✅ Startup notification sent to owner!")
    except Exception as e:
        logger.error(f"❌ Failed to send to owner: {e}")


async def send_shutdown_notification(me):
    """Send shutdown notification to log group"""
    if not LOG_GROUP_ID:
        return
    
    shutdown_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime = f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else f"{hours}h {minutes}m {seconds}s"
    
    text = f"""
🛑 **Bot Stopped**

**Bot:** @{me.username}
**Stopped:** `{shutdown_time}`
**Uptime:** `{uptime}`
**Status:** 🔴 Offline

━━━━━━━━━━━━━━━━━━━━
👋 Bot has been shut down.
    """
    
    try:
        await app.send_message(
            chat_id=LOG_GROUP_ID,
            text=text
        )
        logger.info("✅ Shutdown notification sent to log group!")
    except Exception as e:
        logger.error(f"❌ Failed to send shutdown notification: {e}")


async def start_bot():
    """Start the bot"""
    logger.info("🚀 Starting Waifu Bot...")
    
    # Load modules
    loaded, failed = load_modules()
    
    # Connect to database
    try:
        await db.connect()
        logger.info("📦 Database connected!")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    # Start bot
    await app.start()
    
    # Get bot info
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username}")
    
    # Send startup notifications
    await send_startup_notification(me, loaded, failed)
    
    # Keep bot running
    logger.info("✅ Bot is now idle and ready!")
    await idle()
    
    # Send shutdown notification
    await send_shutdown_notification(me)
    
    # Cleanup
    await app.stop()
    logger.info("👋 Bot stopped!")


# ═══════════════════════════════════════════════════════════════════
#  /help Command Handler (with image)
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command(["help"], prefixes=[".", "/", "!"]))
async def help_handler(client, message):
    """Dynamic help handler with image"""
    
    print(f"📖 [HELP] Command from {message.from_user.first_name}")
    
    # Check if specific module help is requested
    if len(message.command) > 1:
        module_name = message.command[1].lower()
        
        if module_name in LOADED_MODULES:
            info = LOADED_MODULES[module_name]
            await message.reply_text(
                f"📖 **{info['name']} Help**\n\n{info['help']}"
            )
        else:
            await message.reply_text("❌ Module not found!")
        return
    
    # Show module selection menu
    buttons = []
    row = []
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        row.append(
            InlineKeyboardButton(
                info["name"],
                callback_data=f"help_{module_name}"
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("📋 All Commands", callback_data="help_all")
    ])
    
    caption = """
📚 **Waifu Bot Help**

Welcome to the help menu!

Select a module below to view its commands:
"""
    
    # Send with image
    try:
        await message.reply_photo(
            photo=HELP_IMAGE_URL,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        print("✅ [HELP] Sent with image!")
    except Exception as e:
        print(f"⚠️ [HELP] Image failed: {e}")
        # Fallback to text
        await message.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# ═══════════════════════════════════════════════════════════════════
#  Help Callback Handler (with image support)
# ═══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^help_"))
async def help_callback_handler(client, callback):
    """Handle help callbacks with image support"""
    
    data = callback.data.replace("help_", "")
    
    print(f"📖 [HELP] Callback: {data} from {callback.from_user.first_name}")
    
    if data == "all":
        text = get_full_help()
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncated)"
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            print("✅ [HELP] All commands shown")
        except Exception as e:
            print(f"❌ [HELP] Error: {e}")
    
    elif data == "back":
        buttons = []
        row = []
        
        for module_name, info in sorted(LOADED_MODULES.items()):
            row.append(
                InlineKeyboardButton(
                    info["name"],
                    callback_data=f"help_{module_name}"
                )
            )
            if len(row) == 3:  # chnge if needed 2 row 
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([
            InlineKeyboardButton("📋 All Commands", callback_data="help_all")
        ])
        
        caption = """
📚 **Waifu Bot Help**

Select a module to view its commands:
"""
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await callback.message.edit_text(
                    caption,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            print("✅ [HELP] Back to main menu")
        except Exception as e:
            print(f"❌ [HELP] Error: {e}")
    
    elif data in LOADED_MODULES:
        info = LOADED_MODULES[data]
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
        
        text = f"📖 **{info['name']} Help**\n\n{info['help']}"
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            print(f"✅ [HELP] Module '{info['name']}' shown")
        except Exception as e:
            print(f"❌ [HELP] Error: {e}")
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
#  /logs Command Handler (Owner & Sudo only)
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command(["logs"], prefixes=[".", "/", "!"]))
async def logs_handler(client: Client, message: Message):
    """Send bot logs to authorized users"""
    
    user_id = message.from_user.id
    
    # Check if user is owner or sudo
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await message.reply_text(
            "❌ **Access Denied!**\n"
            "This command is only for Owner and Sudo users."
        )
        logger.warning(f"⚠️ Unauthorized /logs attempt by {message.from_user.first_name} ({user_id})")
        return
    
    logger.info(f"📋 /logs command from {message.from_user.first_name} ({user_id})")
    
    # Check if log file exists
    log_file = "bot.log"
    if not os.path.exists(log_file):
        await message.reply_text("❌ **Log file not found!**")
        return
    
    # Get file size
    file_size = os.path.getsize(log_file)
    file_size_mb = file_size / (1024 * 1024)
    
    # Prepare caption
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else f"{hours}h {minutes}m {seconds}s"
    
    caption = f"""
📋 **Bot Logs**

**Requested by:** {message.from_user.mention}
**Time:** `{current_time}`
**Uptime:** `{uptime}`
**File Size:** `{file_size_mb:.2f} MB`

━━━━━━━━━━━━━━━━━━━━
📁 `bot.log`
"""
    
    try:
        # Send to the group/chat where command was used
        await message.reply_document(
            document=log_file,
            caption=caption,
            file_name=f"bot_logs_{current_time.replace(' ', '_').replace(':', '-')}.log"
        )
        logger.info(f"✅ Logs sent to chat {message.chat.id}")
        
        # Also send to user's DM if command was used in a group
        if message.chat.type != "private":
            try:
                await client.send_document(
                    chat_id=user_id,
                    document=log_file,
                    caption=caption + "\n\n📍 _Sent from: " + f"{message.chat.title}_",
                    file_name=f"bot_logs_{current_time.replace(' ', '_').replace(':', '-')}.log"
                )
                await message.reply_text(
                    "📨 **Logs also sent to your DM!**",
                    quote=False
                )
                logger.info(f"✅ Logs also sent to DM of {user_id}")
            except Exception as dm_error:
                logger.error(f"❌ Failed to send logs to DM: {dm_error}")
                await message.reply_text(
                    "⚠️ **Could not send to DM.** Please start the bot in private first.",
                    quote=False
                )
        
    except Exception as e:
        error_msg = f"❌ **Failed to send logs!**\n`{str(e)}`"
        await message.reply_text(error_msg)
        logger.error(f"❌ Failed to send logs: {e}")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║         🎴 WAIFU SMASH BOT 🎴         ║
    ║                                       ║
    ║   Pyrogram Based | MongoDB | Fast     ║
    ╚═══════════════════════════════════════╝
    """)
    
    try:
        asyncio.get_event_loop().run_until_complete(start_bot())
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
