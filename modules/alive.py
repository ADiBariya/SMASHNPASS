# modules/alive.py - 💫 Sexy Awake Module (Professional Edition)

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
__MODULE__ = "Awake"
__HELP__ = """
✨ **Awake Commands**

┃ /awake - Check bot status with sexy stats
┃ /status - Detailed system status  
┃ /uptime - Quick uptime check
┃ /ping - Response time check
"""

# Sexy Image
AWAKE_IMAGE = "https://files.catbox.moe/zm8c7y.jpg"

# Bot start time
BOT_START_TIME = datetime.now()

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"✨ [AWAKE] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_size(bytes_val):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def get_uptime():
    """Get formatted uptime - compact"""
    delta = datetime.now() - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
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
    delta = datetime.now() - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min{'s' if minutes > 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} sec{'s' if seconds > 1 else ''}")
    
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


def create_progress_bar(percent, length=10):
    """Create sexy progress bar"""
    filled = int(percent / (100 / length))
    empty = length - filled
    
    if percent >= 80:
        bar = "🔴" * filled + "⚫" * empty
    elif percent >= 50:
        bar = "🟡" * filled + "⚫" * empty
    else:
        bar = "🟢" * filled + "⚫" * empty
    
    return bar


def get_status_emoji(percent):
    """Get status emoji based on usage"""
    if percent >= 80:
        return "🔴"
    elif percent >= 50:
        return "🟡"
    else:
        return "🟢"


# ═══════════════════════════════════════════════════════════════════
#  /awake Command - Main Sexy Status
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["awake", "alive"], config.COMMAND_PREFIX))
async def awake_command(client: Client, message: Message):
    """Sexy awake command with premium stats"""
    user = message.from_user
    debug(f"Awake command from {user.first_name} ({user.id})")
    
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
        total_users = 0
        total_waifus = 0
        total_smashes = 0
        total_passes = 0

    # Sexy premium text
    text = f"""
〔 ✦ **{config.BOT_NAME.upper()}** ✦ 〕

┏━━━━━━━━━━━━━━━━━━━━━┓
┃      ✨ **I'M AWAKE!** ✨
┗━━━━━━━━━━━━━━━━━━━━━┛

▸ **Status:** 🟢 Online & Ready
▸ **Uptime:** ⏱️ `{uptime}`
▸ **Mode:** 💫 Smashing Waifus

━━━━━━━━━━━━━━━━━━━━━━━━

📊 **STATISTICS**

  ╭───────────────────╮
  │ 👥  Users    ›  `{total_users:,}`
  │ 🎴  Waifus   ›  `{total_waifus:,}`
  │ 💥  Smashes  ›  `{total_smashes:,}`
  │ 👋  Passes   ›  `{total_passes:,}`
  ╰───────────────────╯

"""

    # Add system stats if available
    if sys_stats:
        cpu_status = get_status_emoji(sys_stats['cpu'])
        ram_status = get_status_emoji(sys_stats['ram_percent'])
        
        text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

💻 **SYSTEM**

  ╭───────────────────╮
  │ {cpu_status} CPU    ›  `{sys_stats['cpu']}%`
  │ {ram_status} RAM    ›  `{sys_stats['ram_percent']}%`
  │ 🐍 Python ›  `{platform.python_version()}`
  ╰───────────────────╯

"""

    text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

🔗 **CONNECT**

  ▸ Owner: {config.OWNER_USERNAME}
  ▸ Bot: @{config.BOT_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━━━
     💖 _Thanks for using me!_
"""

    # Premium Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
            InlineKeyboardButton("📊 Stats", callback_data="refresh_status"),
            InlineKeyboardButton("🔄", callback_data="refresh_awake")
        ],
        [
            InlineKeyboardButton("📢 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add Me to Your Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    # Send with image
    try:
        await message.reply_photo(
            photo=AWAKE_IMAGE,
            caption=text,
            reply_markup=buttons
        )
        debug("Awake message sent!")
    except Exception as e:
        debug(f"Image failed: {e}")
        await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /status Command - Detailed System Status
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["status", "sys", "system", "stats"], config.COMMAND_PREFIX))
async def status_command(client: Client, message: Message):
    """Detailed system status with sexy layout"""
    user = message.from_user
    debug(f"Status command from {user.first_name}")
    
    sys_stats = get_system_stats()
    uptime = get_uptime_detailed()
    
    text = f"""
〔 💻 **SYSTEM STATUS** 〕

┏━━━━━━━━━━━━━━━━━━━━━┓
┃   🟢 All Systems Operational
┗━━━━━━━━━━━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━

⏰ **UPTIME**
╭─────────────────────────╮
│ 🕐 {uptime}
│ 📅 Since: {BOT_START_TIME.strftime('%d %b %Y, %H:%M')}
╰─────────────────────────╯

━━━━━━━━━━━━━━━━━━━━━━━━

🔧 **ENVIRONMENT**
╭─────────────────────────╮
│ 🐍 Python  ›  `{platform.python_version()}`
│ 💿 OS      ›  `{platform.system()}`
│ 🏗️ Arch    ›  `{platform.machine()}`
╰─────────────────────────╯
"""
    
    if sys_stats:
        cpu_bar = create_progress_bar(sys_stats['cpu'])
        ram_bar = create_progress_bar(sys_stats['ram_percent'])
        disk_bar = create_progress_bar(sys_stats['disk_percent'])
        
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RESOURCE USAGE**

**🖥️ CPU**
{cpu_bar} `{sys_stats['cpu']}%`

**💾 RAM**
{ram_bar} `{sys_stats['ram_percent']}%`
↳ {sys_stats['ram_used']} / {sys_stats['ram_total']}

**📀 DISK**
{disk_bar} `{sys_stats['disk_percent']}%`
↳ {sys_stats['disk_used']} / {sys_stats['disk_total']}
"""
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🔄 _Updated: {datetime.now().strftime('%H:%M:%S')}_
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /uptime Command - Quick Uptime Check
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["uptime", "up"], config.COMMAND_PREFIX))
async def uptime_command(client: Client, message: Message):
    """Quick uptime command - Clean & Simple"""
    uptime = get_uptime_detailed()
    
    text = f"""
〔 ⏰ **UPTIME** 〕

╭───────────────────────────╮
│
│  🤖 **{config.BOT_NAME}**
│
│  🟢 Status: **ONLINE**
│  
│  ⏱️ Running for:
│  `{uptime}`
│  
│  📅 Started:
│  `{BOT_START_TIME.strftime('%d %b %Y at %H:%M:%S')}`
│
╰───────────────────────────╯
"""
    
    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  /ping Command - Response Time
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["ping", "speed"], config.COMMAND_PREFIX))
async def ping_command(client: Client, message: Message):
    """Check bot response time"""
    start = datetime.now()
    msg = await message.reply_text("🏓 Pinging...")
    end = datetime.now()
    
    ping_ms = (end - start).microseconds / 1000
    
    if ping_ms < 100:
        status = "🟢 Excellent"
    elif ping_ms < 300:
        status = "🟡 Good"
    else:
        status = "🔴 Slow"
    
    text = f"""
〔 🏓 **PONG!** 〕

╭────────────────────╮
│  ⚡ `{ping_ms:.2f}ms`
│  📶 {status}
╰────────────────────╯
"""
    
    await msg.edit_text(text)


# ═══════════════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^refresh_awake$"))
async def refresh_awake_callback(client: Client, callback: CallbackQuery):
    """Refresh awake stats"""
    debug(f"Refresh awake from {callback.from_user.first_name}")
    
    uptime = get_uptime()
    sys_stats = get_system_stats()
    
    try:
        global_stats = db.get_global_stats()
        total_users = global_stats.get("total_users", 0)
        total_waifus = global_stats.get("total_waifus_collected", 0)
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
    except:
        total_users = 0
        total_waifus = 0
        total_smashes = 0
        total_passes = 0
    
    text = f"""
〔 ✦ **{config.BOT_NAME.upper()}** ✦ 〕

┏━━━━━━━━━━━━━━━━━━━━━┓
┃      ✨ **I'M AWAKE!** ✨
┗━━━━━━━━━━━━━━━━━━━━━┛

▸ **Status:** 🟢 Online & Ready
▸ **Uptime:** ⏱️ `{uptime}`
▸ **Mode:** 💫 Smashing Waifus

━━━━━━━━━━━━━━━━━━━━━━━━

📊 **STATISTICS**

  ╭───────────────────╮
  │ 👥  Users    ›  `{total_users:,}`
  │ 🎴  Waifus   ›  `{total_waifus:,}`
  │ 💥  Smashes  ›  `{total_smashes:,}`
  │ 👋  Passes   ›  `{total_passes:,}`
  ╰───────────────────╯

"""

    if sys_stats:
        cpu_status = get_status_emoji(sys_stats['cpu'])
        ram_status = get_status_emoji(sys_stats['ram_percent'])
        
        text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

💻 **SYSTEM**

  ╭───────────────────╮
  │ {cpu_status} CPU    ›  `{sys_stats['cpu']}%`
  │ {ram_status} RAM    ›  `{sys_stats['ram_percent']}%`
  │ 🐍 Python ›  `{platform.python_version()}`
  ╰───────────────────╯

"""

    text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

🔗 **CONNECT**

  ▸ Owner: {config.OWNER_USERNAME}
  ▸ Bot: @{config.BOT_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━━━
  💖 _Thanks for using me!_
  
🔄 _Refreshed: {datetime.now().strftime('%H:%M:%S')}_
"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
            InlineKeyboardButton("📊 Stats", callback_data="refresh_status"),
            InlineKeyboardButton("🔄", callback_data="refresh_awake")
        ],
        [
            InlineKeyboardButton("📢 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add Me to Your Group", 
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
        await callback.answer("❌ No changes", show_alert=False)


@Client.on_callback_query(filters.regex("^show_awake$"))
async def show_awake_callback(client: Client, callback: CallbackQuery):
    """Show awake from callback"""
    debug(f"Show awake callback from {callback.from_user.first_name}")
    
    uptime = get_uptime()
    sys_stats = get_system_stats()
    
    try:
        global_stats = db.get_global_stats()
        total_users = global_stats.get("total_users", 0)
        total_waifus = global_stats.get("total_waifus_collected", 0)
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
    except:
        total_users = 0
        total_waifus = 0
        total_smashes = 0
        total_passes = 0
    
    text = f"""
〔 ✦ **{config.BOT_NAME.upper()}** ✦ 〕

┏━━━━━━━━━━━━━━━━━━━━━┓
┃      ✨ **I'M AWAKE!** ✨
┗━━━━━━━━━━━━━━━━━━━━━┛

▸ **Status:** 🟢 Online & Ready
▸ **Uptime:** ⏱️ `{uptime}`
▸ **Mode:** 💫 Smashing Waifus

━━━━━━━━━━━━━━━━━━━━━━━━

📊 **STATISTICS**

  ╭───────────────────╮
  │ 👥  Users    ›  `{total_users:,}`
  │ 🎴  Waifus   ›  `{total_waifus:,}`
  │ 💥  Smashes  ›  `{total_smashes:,}`
  │ 👋  Passes   ›  `{total_passes:,}`
  ╰───────────────────╯

"""

    if sys_stats:
        cpu_status = get_status_emoji(sys_stats['cpu'])
        ram_status = get_status_emoji(sys_stats['ram_percent'])
        
        text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

💻 **SYSTEM**

  ╭───────────────────╮
  │ {cpu_status} CPU    ›  `{sys_stats['cpu']}%`
  │ {ram_status} RAM    ›  `{sys_stats['ram_percent']}%`
  │ 🐍 Python ›  `{platform.python_version()}`
  ╰───────────────────╯

"""

    text += f"""━━━━━━━━━━━━━━━━━━━━━━━━

🔗 **CONNECT**

  ▸ Owner: {config.OWNER_USERNAME}
  ▸ Bot: @{config.BOT_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━━━
     💖 _Thanks for using me!_
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
            InlineKeyboardButton("📊 Stats", callback_data="refresh_status"),
            InlineKeyboardButton("🔄", callback_data="refresh_awake")
        ],
        [
            InlineKeyboardButton("📢 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_GROUP}")
        ],
        [
            InlineKeyboardButton("➕ Add Me to Your Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Show awake error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^refresh_status$"))
async def refresh_status_callback(client: Client, callback: CallbackQuery):
    """Refresh system status"""
    debug(f"Refresh status from {callback.from_user.first_name}")
    
    sys_stats = get_system_stats()
    uptime = get_uptime_detailed()
    
    text = f"""
〔 💻 **SYSTEM STATUS** 〕

┏━━━━━━━━━━━━━━━━━━━━━┓
┃   🟢 All Systems Operational
┗━━━━━━━━━━━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━

⏰ **UPTIME**
╭─────────────────────────╮
│ 🕐 {uptime}
│ 📅 Since: {BOT_START_TIME.strftime('%d %b %Y, %H:%M')}
╰─────────────────────────╯

━━━━━━━━━━━━━━━━━━━━━━━━

🔧 **ENVIRONMENT**
╭─────────────────────────╮
│ 🐍 Python  ›  `{platform.python_version()}`
│ 💿 OS      ›  `{platform.system()}`
│ 🏗️ Arch    ›  `{platform.machine()}`
╰─────────────────────────╯
"""
    
    if sys_stats:
        cpu_bar = create_progress_bar(sys_stats['cpu'])
        ram_bar = create_progress_bar(sys_stats['ram_percent'])
        disk_bar = create_progress_bar(sys_stats['disk_percent'])
        
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RESOURCE USAGE**

**🖥️ CPU**
{cpu_bar} `{sys_stats['cpu']}%`

**💾 RAM**
{ram_bar} `{sys_stats['ram_percent']}%`
↳ {sys_stats['ram_used']} / {sys_stats['ram_total']}

**📀 DISK**
{disk_bar} `{sys_stats['disk_percent']}%`
↳ {sys_stats['disk_used']} / {sys_stats['disk_total']}
"""
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🔄 _Refreshed: {datetime.now().strftime('%H:%M:%S')}_
"""
    
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
        await callback.answer("❌ No changes", show_alert=False)
