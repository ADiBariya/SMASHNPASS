# modules/start.py - Start Command Module (Fixed)

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ParseMode
from database import db
import config
import time 
from datetime import datetime

# Track time 
BOT_START_TIME = datetime.now()

def get_formatted_uptime():
    """Calculate and return nicely formatted bot uptime"""
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days}d")
    if hours > 0 or uptime_parts:
        uptime_parts.append(f"{hours}h")
    if minutes > 0 or uptime_parts:
        uptime_parts.append(f"{minutes}m")
    uptime_parts.append(f"{seconds}s")
    
    return " ".join(uptime_parts)

# Module info
__MODULE__ = "𝐒𝐭𝐚𝐫𝐭"
__HELP__ = """
🏠 **Start Commands**
/start - Start the bot
/ping - Check latency  
/stats - Your statistics
"""

# Welcome Image
START_VID = "https://files.catbox.moe/ccwzol.mp4"

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"🏠 [START] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  /start Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("start", config.COMMAND_PREFIX))
async def start_command(client: Client, message: Message):
    user = message.from_user
    
    text = f"""
✨ **Welcome {user.first_name}!** ✨

🎮 **Smash or Pass Waifu Game**
Collect your favorite anime waifus!

Tap **Play Now** to begin.
"""

   

    # THEN: Send MENU BUTTONS in a SEPARATE message
    buttons = InlineKeyboardMarkup([
        [
          InlineKeyboardButton("HELP", callback_data="show_help")
        ],
        [
            
            InlineKeyboardButton("PLAY HERE", url=f"https://t.me/Waifusmashsupport"),
            InlineKeyboardButton("UPDATE", url=f"https://t.me/Waifusmashupdates")
        ],
        [
            InlineKeyboardButton("ADD TO GROUP",
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
     # Send with image
    try:
        await message.reply_video(
            video=START_VID,
            caption=text,
            reply_markup=buttons
        )
        debug("Start message sent with image")
    except Exception as e:
        debug(f"Image failed: {e}, sending text only")
        await message.reply_text(text, reply_markup=buttons)
    


# ═══════════════════════════════════════════════════════════════════
#  /help Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help", config.COMMAND_PREFIX))
async def help_command(client: Client, message: Message):
    """Show help menu"""
    debug(f"Help command from {message.from_user.id}")
    
    text = """
📖 **Help Menu** 📖

━━━━━━━━━━━━━━━━━━━━━
🎮 **Game Commands**
━━━━━━━━━━━━━━━━━━━━━
├ `/smash` - Start a new game
├ `/collection` - View your waifus
├ `/profile` - Your profile
├ `/stats` - Your statistics
└ `/daily` - Claim daily reward

━━━━━━━━━━━━━━━━━━━━━
💰 **Economy**
━━━━━━━━━━━━━━━━━━━━━
├ `/balance` - Check coins
├ `/shop` - Visit shop
├ `/gift` - Gift waifu/coins
└ `/trade` - Trade waifus

━━━━━━━━━━━━━━━━━━━━━
🏆 **Social**
━━━━━━━━━━━━━━━━━━━━━
├ `/top` - Leaderboard
├ `/profile @user` - View profile
└ `/ping` - Bot latency

💡 **Tip:** Legendary waifus are super rare!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 BACK", callback_data="back_start")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /stats Command  
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["stats", "mystats"], config.COMMAND_PREFIX))
async def stats_command(client: Client, message: Message):
    """View user statistics"""
    user = message.from_user
    
    try:
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        collection_count = db.get_collection_count(user.id)
    except Exception as e:
        await message.reply_text(f"❌ Database error: {e}")
        return
    
    total_smash = user_data.get('total_smash', 0)
    total_wins = user_data.get('total_wins', 0)
    win_rate = (total_wins / total_smash * 100) if total_smash > 0 else 0
    
    text = f"""
📊 **Stats for {user.first_name}**

━━━━━━━━━━━━━━━━━━━━━
💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus:** {collection_count}
━━━━━━━━━━━━━━━━━━━━━

🎮 **Game Stats:**
├ 🎯 Smashes: {total_smash}
├ 👋 Passes: {user_data.get('total_pass', 0)}
├ ✅ Wins: {total_wins}
└ ❌ Losses: {user_data.get('total_losses', 0)}

📈 **Win Rate:** {win_rate:.1f}%
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 BACK", callback_data="back_start")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  CALLBACKS - All Fixed
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^show_help$"))
async def help_callback(client: Client, callback: CallbackQuery):
    """Help menu callback - FIXED"""
    user = callback.from_user
    debug(f"Help callback from {user.first_name} ({user.id})")
    
    text = """
📖 **Help Menu** 📖

━━━━━━━━━━━━━━━━━━━━━
🎮 **Game Commands**
━━━━━━━━━━━━━━━━━━━━━
├ `/smash` - Start a new game
├ `/collection` - View your waifus
├ `/profile` - Your profile
├ `/stats` - Your statistics
└ `/daily` - Claim daily reward

━━━━━━━━━━━━━━━━━━━━━
💰 **Economy**
━━━━━━━━━━━━━━━━━━━━━
├ `/balance` - Check coins
├ `/shop` - Visit shop
├ `/gift` - Gift waifu/coins
└ `/trade` - Trade waifus

━━━━━━━━━━━━━━━━━━━━━
🏆 **Social**
━━━━━━━━━━━━━━━━━━━━━
├ `/top` - Leaderboard
├ `/profile @user` - View profile
└ `/ping` - Bot latency

💡 **Tip:** Legendary waifus are super rare!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 BACK", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.video:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
        debug("Help menu displayed!")
    except Exception as e:
        debug(f"Help callback error: {e}")
        # Try sending new message if edit fails
        try:
            await callback.message.reply_text(text, reply_markup=buttons)
        except:
            pass
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^view_stats$"))
async def view_stats_callback(client: Client, callback: CallbackQuery):
    """View stats callback"""
    user = callback.from_user
    debug(f"Stats callback from {user.first_name}")
    
    try:
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        collection_count = db.get_collection_count(user.id)
    except Exception as e:
        debug(f"Stats DB error: {e}")
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    total_smash = user_data.get('total_smash', 0)
    total_wins = user_data.get('total_wins', 0)
    win_rate = (total_wins / total_smash * 100) if total_smash > 0 else 0
    
    text = f"""
📊 **Stats for {user.first_name}**

━━━━━━━━━━━━━━━━━━━━━
💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus:** {collection_count}
📈 **Win Rate:** {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━━

🎮 **Games Played:**
├ ✅ Wins: {total_wins}
└ ❌ Losses: {user_data.get('total_losses', 0)}
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.video:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Stats edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^back_start$"))
async def back_start_callback(client: Client, callback: CallbackQuery):
    """Back to start callback"""
    user = callback.from_user
    debug(f"Back callback from {user.first_name}")
    
    text = f"""
✨ **Welcome {user.first_name}!** ✨

━━━━━━━━━━━━━━━━━━━━━
🎮 **Smash or Pass Waifu Game**
━━━━━━━━━━━━━━━━━━━━━

Use the buttons below to navigate!
"""
    
    buttons = InlineKeyboardMarkup([
        [
          InlineKeyboardButton("HELP", callback_data="show_help")
        ],
        [
            
            InlineKeyboardButton("PLAY HERE", url=f"https://t.me/Waifusmashsupport"),
            InlineKeyboardButton("UPDATE", url=f"https://t.me/Waifusmashupdate")
        ],
        [
            InlineKeyboardButton("ADD TO GROUP",
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]

    ])
    
    try:
        if callback.message.video:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Back edit error: {e}")
    
    await callback.answer()
