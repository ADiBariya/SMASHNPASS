# modules/alive.py - Sexy Alive Module (Clean Version)

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from datetime import datetime
import platform
import psutil
import config
from database import db

# Module info
__MODULE__ = "Alive"
__HELP__ = """
💗 **Alive Commands**
/alive - Check if bot is alive with sexy stats
/status - Detailed bot status
/uptime - Bot uptime info
"""

# Use the same START_IMAGE
ALIVE_IMAGE = "https://files.catbox.moe/jcy3qf.jpg"

# Bot start time
BOT_START_TIME = datetime.now()

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"💗 [ALIVE] {msg}")


def get_size(bytes_val):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def get_uptime():
    """Get formatted uptime"""
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)


def get_uptime_detailed():
    """Get detailed uptime string"""
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    
    return ", ".join(parts)


def get_system_stats():
    """Get system statistics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": cpu_percent,
            "ram_used": get_size(memory.used),
            "ram_total": get_size(memory.total),
            "ram_percent": memory.percent,
            "disk_used": get_size(disk.used),
            "disk_total": get_size(disk.total),
            "disk_percent": disk.percent
        }
    except:
        return None


# ═══════════════════════════════════════════════════════════════════
#  /alive Command - Main Sexy Alive
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["alive", "awake", "online"], config.COMMAND_PREFIX))
async def alive_command(client: Client, message: Message):
    """Sexy alive command with full stats"""
    user = message.from_user
    debug(f"Alive command from {user.first_name} ({user.id})")
    
    # Get stats
    uptime = get_uptime()
    sys_stats = get_system_stats()
    
    # Get bot stats from database
    try:
        global_stats = db.get_global_stats()
        total_users = global_stats.get("total_users", 0)
        total_waifus = global_stats.get("total_waifus_collected", 0)
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
    except:
        total_users = "N/A"
        total_waifus = "N/A"
        total_smashes = "N/A"
        total_passes = "N/A"
    
    # Sexy alive text
    text = f"""
╔═══════════════════════════════╗
       💗 **I'M ALIVE BABY!** 💗
╚═══════════════════════════════╝

✨ **{config.BOT_NAME}** is online and ready!

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **UPTIME**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🕐 Running for: `{uptime}`
┃ 📅 Since: `{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **BOT STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👥 Total Users: `{total_users:,}` 
┃ 📦 Waifus Collected: `{total_waifus:,}`
┃ 💥 Total Smashes: `{total_smashes:,}`
┃ 👋 Total Passes: `{total_passes:,}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Add system stats if available
    if sys_stats:
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
💻 **SYSTEM STATUS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🖥️ CPU: `{sys_stats['cpu']}%`
┃ 💾 RAM: `{sys_stats['ram_used']}/{sys_stats['ram_total']}` ({sys_stats['ram_percent']}%)
┃ 📀 Disk: `{sys_stats['disk_used']}/{sys_stats['disk_total']}` ({sys_stats['disk_percent']}%)
┃ 🐍 Python: `{platform.python_version()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **QUICK LINKS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👨‍💻 Owner: @{config.OWNER_USERNAME}
┃ 🤖 Bot: @{config.BOT_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━

💖 **Thanks for using me!** 💖
"""

    # Clean Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_alive")
        ],
        [
            InlineKeyboardButton("🆕 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add to Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    # Send with image
    try:
        await message.reply_photo(
            photo=ALIVE_IMAGE,
            caption=text,
            reply_markup=buttons
        )
        debug("Alive message sent with image!")
    except Exception as e:
        debug(f"Image failed: {e}, sending text only")
        await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /status Command - Detailed Status
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["status", "sys", "system"], config.COMMAND_PREFIX))
async def status_command(client: Client, message: Message):
    """Detailed system status"""
    user = message.from_user
    debug(f"Status command from {user.first_name}")
    
    sys_stats = get_system_stats()
    uptime = get_uptime_detailed()
    
    text = f"""
🖥️ **SYSTEM STATUS**

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **UPTIME**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🕐 {uptime}
┃ 📅 Started: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 **ENVIRONMENT**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🐍 Python: `{platform.python_version()}`
┃ 💿 OS: `{platform.system()} {platform.release()}`
┃ 🏗️ Architecture: `{platform.machine()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    if sys_stats:
        # Progress bars
        cpu_bar = "█" * int(sys_stats['cpu'] / 10) + "░" * (10 - int(sys_stats['cpu'] / 10))
        ram_bar = "█" * int(sys_stats['ram_percent'] / 10) + "░" * (10 - int(sys_stats['ram_percent'] / 10))
        disk_bar = "█" * int(sys_stats['disk_percent'] / 10) + "░" * (10 - int(sys_stats['disk_percent'] / 10))
        
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESOURCE USAGE**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 
┃ 🖥️ **CPU Usage**
┃ [{cpu_bar}] {sys_stats['cpu']}%
┃ 
┃ 💾 **RAM Usage**
┃ [{ram_bar}] {sys_stats['ram_percent']}%
┃ Used: {sys_stats['ram_used']} / {sys_stats['ram_total']}
┃ 
┃ 📀 **Disk Usage**
┃ [{disk_bar}] {sys_stats['disk_percent']}%
┃ Used: {sys_stats['disk_used']} / {sys_stats['disk_total']}
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    text += "\n✅ **All systems operational!**"
    
    # Only Refresh and Back buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /uptime Command - Simple Uptime (No Buttons)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["uptime", "up"], config.COMMAND_PREFIX))
async def uptime_command(client: Client, message: Message):
    """Simple uptime command - No buttons"""
    uptime = get_uptime_detailed()
    
    text = f"""
⏰ **BOT UPTIME**

━━━━━━━━━━━━━━━━━━━━━
🤖 **{config.BOT_NAME}**
━━━━━━━━━━━━━━━━━━━━━

🕐 **Running for:**
`{uptime}`

📅 **Started at:**
`{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}`

✅ Status: **ONLINE**
"""
    
    # No buttons
    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^refresh_alive$"))
async def refresh_alive_callback(client: Client, callback: CallbackQuery):
    """Refresh alive stats"""
    debug(f"Refresh alive from {callback.from_user.first_name}")
    
    uptime = get_uptime()
    sys_stats = get_system_stats()
    
    try:
        global_stats = db.get_global_stats()
        total_users = global_stats.get("total_users", 0)
        total_waifus = global_stats.get("total_waifus_collected", 0)
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
    except:
        total_users = "N/A"
        total_waifus = "N/A"
        total_smashes = "N/A"
        total_passes = "N/A"
    
    text = f"""
╔═══════════════════════════════╗
       💗 **I'M ALIVE BABY!** 💗
╚═══════════════════════════════╝

✨ **{config.BOT_NAME}** is online and ready!

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **UPTIME**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🕐 Running for: `{uptime}`
┃ 📅 Since: `{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **BOT STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👥 Total Users: `{total_users:,}` 
┃ 📦 Waifus Collected: `{total_waifus:,}`
┃ 💥 Total Smashes: `{total_smashes:,}`
┃ 👋 Total Passes: `{total_passes:,}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    if sys_stats:
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
💻 **SYSTEM STATUS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🖥️ CPU: `{sys_stats['cpu']}%`
┃ 💾 RAM: `{sys_stats['ram_used']}/{sys_stats['ram_total']}` ({sys_stats['ram_percent']}%)
┃ 📀 Disk: `{sys_stats['disk_used']}/{sys_stats['disk_total']}` ({sys_stats['disk_percent']}%)
┃ 🐍 Python: `{platform.python_version()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **QUICK LINKS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👨‍💻 Owner: @{config.OWNER_USERNAME}
┃ 🤖 Bot: @{config.BOT_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━

💖 **Thanks for using me!** 💖

🔄 _Last refreshed: {datetime.now().strftime('%H:%M:%S')}_
"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_alive")
        ],
        [
            InlineKeyboardButton("🆕 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add to Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer("✅ Refreshed!", show_alert=False)
    except Exception as e:
        debug(f"Refresh error: {e}")
        await callback.answer("❌ Error refreshing", show_alert=True)


@Client.on_callback_query(filters.regex("^show_alive$"))
async def show_alive_callback(client: Client, callback: CallbackQuery):
    """Show alive from callback"""
    debug(f"Show alive callback from {callback.from_user.first_name}")
    
    uptime = get_uptime()
    sys_stats = get_system_stats()
    
    try:
        global_stats = db.get_global_stats()
        total_users = global_stats.get("total_users", 0)
        total_waifus = global_stats.get("total_waifus_collected", 0)
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
    except:
        total_users = "N/A"
        total_waifus = "N/A"
        total_smashes = "N/A"
        total_passes = "N/A"
    
    text = f"""
╔═══════════════════════════════╗
       💗 **I'M ALIVE BABY!** 💗
╚═══════════════════════════════╝

✨ **{config.BOT_NAME}** is online and ready!

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **UPTIME**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🕐 Running for: `{uptime}`
┃ 📅 Since: `{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **BOT STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👥 Total Users: `{total_users:,}` 
┃ 📦 Waifus Collected: `{total_waifus:,}`
┃ 💥 Total Smashes: `{total_smashes:,}`
┃ 👋 Total Passes: `{total_passes:,}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    if sys_stats:
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
💻 **SYSTEM STATUS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🖥️ CPU: `{sys_stats['cpu']}%`
┃ 💾 RAM: `{sys_stats['ram_used']}/{sys_stats['ram_total']}` ({sys_stats['ram_percent']}%)
┃ 🐍 Python: `{platform.python_version()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **QUICK LINKS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 👨‍💻 Owner: @{config.OWNER_USERNAME}
┃ 🤖 Bot: @{config.BOT_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━

💖 **Thanks for using me!** 💖
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_alive")
        ],
        [
            InlineKeyboardButton("🆕 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add to Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Show alive error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^refresh_status$"))
async def refresh_status_callback(client: Client, callback: CallbackQuery):
    """Refresh system status"""
    debug(f"Refresh status from {callback.from_user.first_name}")
    
    sys_stats = get_system_stats()
    uptime = get_uptime_detailed()
    
    text = f"""
🖥️ **SYSTEM STATUS**

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **UPTIME**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🕐 {uptime}
┃ 📅 Started: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 **ENVIRONMENT**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 🐍 Python: `{platform.python_version()}`
┃ 💿 OS: `{platform.system()} {platform.release()}`
┃ 🏗️ Architecture: `{platform.machine()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    if sys_stats:
        cpu_bar = "█" * int(sys_stats['cpu'] / 10) + "░" * (10 - int(sys_stats['cpu'] / 10))
        ram_bar = "█" * int(sys_stats['ram_percent'] / 10) + "░" * (10 - int(sys_stats['ram_percent'] / 10))
        disk_bar = "█" * int(sys_stats['disk_percent'] / 10) + "░" * (10 - int(sys_stats['disk_percent'] / 10))
        
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESOURCE USAGE**
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 
┃ 🖥️ **CPU:** [{cpu_bar}] {sys_stats['cpu']}%
┃ 
┃ 💾 **RAM:** [{ram_bar}] {sys_stats['ram_percent']}%
┃ {sys_stats['ram_used']} / {sys_stats['ram_total']}
┃ 
┃ 📀 **Disk:** [{disk_bar}] {sys_stats['disk_percent']}%
┃ {sys_stats['disk_used']} / {sys_stats['disk_total']}
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    text += f"\n✅ All systems operational!\n\n🔄 _Refreshed: {datetime.now().strftime('%H:%M:%S')}_"
    
    # Only Refresh and Back buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer("✅ Refreshed!", show_alert=False)
    except Exception as e:
        debug(f"Status refresh error: {e}")
        await callback.answer("❌ Error", show_alert=True)
