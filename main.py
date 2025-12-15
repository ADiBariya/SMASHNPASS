import os
import sys
import asyncio
import importlib
import logging
import config
from pathlib import Path
from datetime import datetime
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN
from database import db
from helpers.utils import get_waifu_manager
from core.user_client import user
logging.getLogger("pyrogram").setLevel(logging.WARNING)


OWNER_ID = int(os.environ.get("OWNER_ID", "1432702628"))
sudo_default = "1737646273"
SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", sudo_default).split()))

# Ensure owner is in sudo list
if OWNER_ID not in SUDO_USERS:
    SUDO_USERS.append(OWNER_ID)

# ============================
#  LOGGING CONFIGURATION
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ============================
#  BOT INITIALIZATION
# ============================
app = Client(
    name="WaifuBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="modules")
)

# Global variables
LOADED_MODULES = {}
BOT_START_TIME = datetime.now()
STARTUP_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"
HELP_IMAGE_URL = "https://files.catbox.moe/9lkbyr.jpg"

try:
    from config import LOG_GROUP_ID
except ImportError:
    LOG_GROUP_ID = None
    logger.warning("⚠️ LOG_GROUP_ID missing — log notifications disabled.")


# ============================
# GROUP SCANNER FUNCTION
# ============================
async def scan_all_groups(client: Client):
    """
    Scan all dialogs to find groups bot is in.
    Called on startup to sync all groups to database.
    """
    from pyrogram.enums import ChatType
    
    logger.info("🔍 Starting group scan...")
    
    groups_found = 0
    supergroups_found = 0
    errors = 0
    
    try:
        async for dialog in client.get_dialogs():
            try:
                chat = dialog.chat
                
                # Only process groups and supergroups
                if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    # Get member count if possible
                    try:
                        member_count = await client.get_chat_members_count(chat.id)
                    except:
                        member_count = 0
                    
                    # Save to database
                    db.get_or_create_group(
                        chat_id=chat.id,
                        title=chat.title,
                        username=getattr(chat, 'username', None)
                    )
                    
                    # Update member count
                    db.update_group_member_count(chat.id, member_count)
                    
                    if chat.type == ChatType.SUPERGROUP:
                        supergroups_found += 1
                    else:
                        groups_found += 1
                    
                    logger.debug(f"📌 Found group: {chat.title} ({chat.id})")
                    
                    # Small delay to avoid flood
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                errors += 1
                logger.warning(f"Error processing dialog: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scanning dialogs: {e}")
    
    total = groups_found + supergroups_found
    logger.info(f"✅ Group scan complete! Found {total} groups ({groups_found} groups, {supergroups_found} supergroups)")
    
    return {
        "total": total,
        "groups": groups_found,
        "supergroups": supergroups_found,
        "errors": errors
    }


# ============================
# MODULE LOADER
# ============================
def load_modules():
    """Load all modules from modules folder"""
    modules_path = Path("modules")
    if not modules_path.exists():
        logger.error("❌ Modules folder not found!")
        return 0, 0

    loaded, failed = 0, 0
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
            logger.error(f"❌ Failed to load module {module_name}: {e}")

    logger.info(f"📦 Modules loaded: {loaded} | Failed: {failed}")
    return loaded, failed


# ============================
# HELP SYSTEM
# ============================
def get_full_help():
    """Generate full help text"""
    text = "📚 **WAIFU BOT HELP**\n\n"
    for name, info in sorted(LOADED_MODULES.items()):
        text += f"**{info['name']}**\n{info['help']}\n\n"
    return text


# ============================
# STARTUP NOTIFICATION
# ============================
async def send_startup_notification(me, loaded, failed, group_stats=None):
    """Send startup notification to log group and owner"""
    startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Group stats section
    group_section = ""
    if group_stats:
        group_section = f"""
**Group Sync:**
├ 💬 **Groups:** {group_stats.get('groups', 0)}
├ 🔷 **Supergroups:** {group_stats.get('supergroups', 0)}
├ 📊 **Total:** {group_stats.get('total', 0)}
└ ⚠️ **Errors:** {group_stats.get('errors', 0)}
"""

    caption = f"""
🚀 **Bot Started Successfully!**

**Bot Information:**
├ **Username:** @{me.username}
├ **Bot ID:** `{me.id}`
├ **Name:** {me.first_name}
└ **Started:** `{startup_time}`

**Module Status:**
├ ✅ **Loaded:** {loaded}
├ ❌ **Failed:** {failed}
└ 📊 **Total:** {loaded + failed}
{group_section}
**System Status:**
├ 🗄️ **Database:** Connected
├ 🔧 **Plugins:** Active
└ 🟢 **Status:** Online

━━━━━━━━━━━━━━━━━━━━
⏰ **Bot is now running!**
"""

    # Send to log group if configured
    if LOG_GROUP_ID:
        try:
            await app.send_photo(LOG_GROUP_ID, STARTUP_IMAGE_URL, caption)
            logger.info("✅ Startup message sent to LOG_GROUP_ID.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send startup photo to LOG_GROUP_ID: {e}")
            try:
                await app.send_message(LOG_GROUP_ID, caption)
            except Exception as e2:
                logger.error(f"❌ Failed to send startup text to LOG_GROUP_ID: {e2}")

    # Send to owner
    try:
        await app.send_message(OWNER_ID, caption)
        logger.info("✅ Startup message sent to OWNER_ID.")
    except Exception as e:
        logger.warning(f"⚠️ Couldn't send startup DM to owner: {e}")


# ============================
# SHUTDOWN NOTIFICATION
# ============================
async def send_shutdown_notification(me):
    """Send shutdown notification to log group"""
    if not LOG_GROUP_ID:
        return

    uptime = datetime.now() - BOT_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else f"{hours}h {minutes}m {seconds}s"

    # Get final stats
    total_users = db.get_total_users()
    total_groups = db.get_total_groups()

    text = f"""
🛑 **Bot Stopped**

**Bot:** @{me.username}
**Uptime:** `{uptime_str}`

**Final Stats:**
├ 👥 **Users:** {total_users:,}
└ 💬 **Groups:** {total_groups:,}

━━━━━━━━━━━━━━━━━━━━
👋 Bot has been shut down.
"""
    try:
        await app.send_message(LOG_GROUP_ID, text)
        logger.info("🛑 Sent shutdown message to LOG_GROUP_ID")
    except Exception as e:
        logger.error(f"❌ Failed to send shutdown message: {e}")


# ============================
# HELP COMMAND
# ============================
@app.on_message(filters.command(["help"], [".", "/", "!"]))
async def help_cmd(client, message: Message):
    """Help command handler with image support"""
    buttons, row = [], []
    for mod, info in sorted(LOADED_MODULES.items()):
        row.append(InlineKeyboardButton(info["name"], callback_data=f"help_{mod}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("𝐁𝐀𝐂𝐊", callback_data="back_start")])

    caption = """
📚 **Waifu Bot Help**
Select a module to view its commands:
"""
    try:
        await message.reply_photo(HELP_IMAGE_URL, caption, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.warning(f"⚠️ Failed to send help image: {e}")
        await message.reply_text(caption, reply_markup=InlineKeyboardMarkup(buttons))


# ============================
# HELP CALLBACK
# ============================
@app.on_callback_query(filters.regex("^help_"))
async def help_callback(client, cb):
    """Handle help callbacks"""
    module = cb.data.replace("help_", "")

    if module == "all":
        text = get_full_help()
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "help_back")]]))
        return

    if module == "back":
        buttons, row = [], []
        for mod, info in sorted(LOADED_MODULES.items()):
            row.append(InlineKeyboardButton(info["name"], callback_data=f"help_{mod}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("𝐁𝐀𝐂𝐊", callback_data="back_start")])
        await cb.message.edit_text("📚 **Help Menu**", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if module in LOADED_MODULES:
        info = LOADED_MODULES[module]
        text = f"📖 **{info['name']}**\n\n{info['help']}"
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "help_back")]]))

    await cb.answer()


# ============================
# LOGS COMMAND (Owner & Sudo Only)
# ============================
@app.on_message(filters.command(["logs"], [".", "/", "!"]))
async def logs_handler(client, message: Message):
    """Send logs to authorized users only"""
    user_id = message.from_user.id

    # Check if user is owner or sudo
    if user_id not in SUDO_USERS and user_id != OWNER_ID:
        return await message.reply_text("❌ **Access Denied!** Only owner or sudo can access logs.")

    log_path = "bot.log"
    if not os.path.exists(log_path):
        return await message.reply_text("⚠️ **No log file found!**")

    # Get file info
    file_size = os.path.getsize(log_path)
    size_mb = file_size / (1024 * 1024)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    caption = f"""
📋 **Bot Logs**
**Requested by:** {message.from_user.mention}
📁 **Size:** {size_mb:.2f} MB
⏰ **Generated at:** `{timestamp}`
━━━━━━━━━━━━━━━━━━━━
"""

    # Send to chat first
    try:
        await message.reply_document(
            document=log_path,
            caption=caption,
            file_name=f"bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        logger.info(f"📤 Logs sent in chat to {message.from_user.first_name} ({user_id})")
    except Exception as e:
        logger.error(f"❌ Failed to send logs in chat: {e}")
        return await message.reply_text(f"❌ Failed to send logs: {str(e)}")

    # Try sending DM as well
    try:
        await client.send_document(
            chat_id=user_id,
            document=log_path,
            caption="📬 **Here's your DM copy of the log file.**",
            file_name=f"bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        logger.info(f"📥 Logs sent by DM to {user_id}")
        await message.reply_text("📬 **Logs sent!** A copy has also been sent to your DM.")
    except Exception as e:
        logger.warning(f"⚠️ DM logs failed to send: {e}")
        await message.reply_text("⚠️ Could not send to your DM. Make sure you've started the bot in private.")


# ============================
# MANUAL GROUP SCAN COMMAND
# ============================
@app.on_message(filters.command(["scangroups", "syncgroups"], [".", "/", "!"]))
async def scan_groups_cmd(client, message: Message):
    """Manually trigger group scan - Owner/Sudo only"""
    user_id = message.from_user.id
    
    if user_id not in SUDO_USERS and user_id != OWNER_ID:
        return await message.reply_text("❌ **Access Denied!**")
    
    status_msg = await message.reply_text("🔍 **Scanning all groups...** This may take a while.")
    
    try:
        stats = await scan_all_groups(client)
        
        await status_msg.edit_text(
            f"✅ **Group Scan Complete!**\n\n"
            f"📊 **Results:**\n"
            f"├ 💬 Groups: {stats['groups']}\n"
            f"├ 🔷 Supergroups: {stats['supergroups']}\n"
            f"├ 📊 Total: {stats['total']}\n"
            f"└ ⚠️ Errors: {stats['errors']}\n\n"
            f"All groups have been synced to database!"
        )
        
        # Log to log group
        if LOG_GROUP_ID:
            await client.send_message(
                LOG_GROUP_ID,
                f"🔍 **Manual Group Scan Triggered**\n\n"
                f"**By:** {message.from_user.mention}\n"
                f"**Total Groups Found:** {stats['total']}"
            )
            
    except Exception as e:
        logger.error(f"Error in group scan: {e}")
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")


# ============================
# BOT STATS QUICK COMMAND
# ============================
@app.on_message(filters.command(["ping"], [".", "/", "!"]))
async def ping_cmd(client, message: Message):
    """Quick ping check"""
    import time
    
    start = time.time()
    msg = await message.reply_text("🏓 **Pong!**")
    end = time.time()
    
    latency = (end - start) * 1000
    uptime = datetime.now() - BOT_START_TIME
    
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    else:
        uptime_str = f"{minutes}m {seconds}s"
    
    await msg.edit_text(
        f"🏓 **Pong!**\n\n"
        f"⚡ **Latency:** `{latency:.2f}ms`\n"
        f"⏰ **Uptime:** `{uptime_str}`\n"
        f"🟢 **Status:** Online"
    )


# ============================
# RESTART COMMAND (Owner Only)
# ============================
@app.on_message(filters.command(["restart", "reboot"], [".", "/", "!"]))
async def restart_cmd(client, message: Message):
    """Restart the bot - Owner only"""
    if message.from_user.id not in OWNER_ID:
        return await message.reply_text("❌ **Owner only command!**")
    
    await message.reply_text("🔄 **Restarting bot...**")
    
    # Send shutdown notification
    me = await client.get_me()
    await send_shutdown_notification(me)
    
    logger.info("🔄 Restart initiated by owner")
    
    # Restart the script
    os.execl(sys.executable, sys.executable, *sys.argv)
# ============================
# START BOT TASK
# ============================
async def start_bot():
    """Start the bot with proper initialization"""
    logger.info("🚀 Starting WaifuBot...")
    logger.info("📡 MongoDB auto-connected.")

    loaded, failed = load_modules()

    await app.start()
    me = await app.get_me()

    logger.info(f"🤖 Logged in as @{me.username}")
    
    # ============================
    # SCAN ALL GROUPS ON STARTUP
    # ============================
    logger.info("🔍 Scanning all groups...")
    group_stats = await scan_all_groups(app)
    logger.info(f"📊 Group scan complete: {group_stats['total']} groups found")
    

    wm = get_waifu_manager()
    CHANNEL_ID = -1003322377810
    
    # 🔥 START USER CLIENT ONCE (NO CONNECT AFTER THIS)
    await user.start()

    logger.info("🔄 Loading Telegram waifus via USER SESSION...")
    await wm.load_channel_waifus(user, CHANNEL_ID)
    logger.info("✅ Telegram waifus loaded!")
  
    await send_startup_notification(me, loaded, failed, group_stats)

    logger.info("🟢 Bot is now idle and ready.")
    await idle()

    await send_shutdown_notification(me)
    await user.stop()
    await app.stop()
    logger.info("🔴 Bot stopped!")

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║         🎴 WAIFU SMASH BOT 🎴         ║
    ║                                       ║
    ║   Pyrogram Based | MongoDB | Fast     ║
    ╚═══════════════════════════════════════╝
    """)

    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"👥 Sudo Users: {SUDO_USERS}")
    print(f"📊 Total Sudo Users: {len(SUDO_USERS)}")

    try:
        asyncio.get_event_loop().run_until_complete(start_bot())
    except KeyboardInterrupt:
        logger.warning("🔻 Interrupted manually.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal Startup Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
