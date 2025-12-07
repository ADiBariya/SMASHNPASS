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
__MODULE__ = "Start"
__HELP__ = """
🏠 **Start Commands**
/start - Start the bot
/ping - Check latency  
/stats - Your statistics
"""

# Welcome Image
START_IMAGE = "https://files.catbox.moe/jcy3qf.jpg"

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
    """Handle /start command"""
    user = message.from_user
    debug(f"Start command from {user.first_name} ({user.id})")
    
    # Database
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except Exception as e:
        debug(f"DB error: {e}")
    
    # Welcome text
    text = f"""
✨ **Welcome {user.first_name}!** ✨

━━━━━━━━━━━━━━━━━━━━━
🎮 **Smash or Pass Waifu Game**
━━━━━━━━━━━━━━━━━━━━━

Collect your favorite anime waifus!

🎯 **How to Play:**
├ Use /smash to get a random waifu
├ Choose **💥 Smash** to try winning her
├ Choose **👋 Pass** to skip
└ If you win, she joins your collection!

✨ **Ready? Tap Play Now!**
"""
    
    # Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("📖 Help", callback_data="show_help"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="view_profile"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="view_lb")
        ],
        [
            InlineKeyboardButton("➕ Add to Group", 
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    # Send with image
    try:
        await message.reply_photo(
            photo=START_IMAGE,
            caption=text,
            reply_markup=buttons
        )
        debug("Start message sent with image")
    except Exception as e:
        debug(f"Image failed: {e}, sending text only")
        await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /ping Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("ping", config.COMMAND_PREFIX))
async def ping_command(client: Client, message: Message):
    """Check bot latency and uptime"""
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    
    latency = (end - start) * 1000
    uptime = get_formatted_uptime()
    
    await msg.edit_text(
        f"🏓 **Pong!**\n\n"
        f"⚡ **Latency:** `{latency:.2f}ms`\n"
        f"⏳ **Uptime:** `{uptime}`"
    )


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
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
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
            InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
            InlineKeyboardButton("🎮 Play", callback_data="play_smash")
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="view_profile")
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
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.photo:
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
            InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
            InlineKeyboardButton("👤 Profile", callback_data="view_profile")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.photo:
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
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("📖 Help", callback_data="show_help"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="view_profile"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="view_lb")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Back edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^view_collection$"))
async def view_collection_callback(client: Client, callback: CallbackQuery):
    """View collection callback"""
    user = callback.from_user
    debug(f"Collection callback from {user.first_name}")
    
    try:
        collection = db.get_user_collection(user.id)
    except Exception as e:
        debug(f"Collection DB error: {e}")
        await callback.answer("❌ Database error!", show_alert=True)
        return
    
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }
    
    if not collection:
        text = f"""
📦 **{user.first_name}'s Collection**

━━━━━━━━━━━━━━━━━━━━━
😢 **Your collection is empty!**
━━━━━━━━━━━━━━━━━━━━━

Play /smash to win waifus!
"""
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
                InlineKeyboardButton("🔙 Back", callback_data="back_start")
            ]
        ])
    else:
        text = f"""
📦 **{user.first_name}'s Collection**

━━━━━━━━━━━━━━━━━━━━━
📊 **Total Waifus:** {len(collection)}
━━━━━━━━━━━━━━━━━━━━━

"""
        for i, waifu in enumerate(collection[:5], 1):
            rarity = waifu.get("waifu_rarity") or waifu.get("rarity", "common")
            emoji = rarity_emojis.get(str(rarity).lower(), "⚪")
            name = waifu.get("waifu_name") or waifu.get("name", "Unknown")
            power = waifu.get("waifu_power") or waifu.get("power", 0)
            text += f"{i}. {emoji} **{name}** (⚔️ {power})\n"
        
        if len(collection) > 5:
            text += f"\n... and {len(collection) - 5} more!"
        
        text += "\n\n📝 Use `/collection` for full list!"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Play More", callback_data="play_smash"),
                InlineKeyboardButton("🔙 Back", callback_data="back_start")
            ]
        ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
        debug("Collection displayed!")
    except Exception as e:
        debug(f"Collection edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^view_profile$"))
async def view_profile_callback(client: Client, callback: CallbackQuery):
    """View profile callback"""
    user = callback.from_user
    debug(f"Profile callback from {user.first_name}")
    
    try:
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        collection = db.get_user_collection(user.id)
        collection_count = len(collection) if collection else 0
    except Exception as e:
        debug(f"Profile DB error: {e}")
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    coins = user_data.get('coins', 0)
    wins = user_data.get('total_wins', 0)
    losses = user_data.get('total_losses', 0)
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    # Count rarities
    rarity_count = {"legendary": 0, "epic": 0, "rare": 0, "common": 0}
    if collection:
        for w in collection:
            r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
            if r in rarity_count:
                rarity_count[r] += 1
    
    text = f"""
👤 **{user.first_name}'s Profile**

━━━━━━━━━━━━━━━━━━━━━
📋 **Info**
━━━━━━━━━━━━━━━━━━━━━
├ 🆔 ID: `{user.id}`
├ 👤 Username: @{user.username or 'None'}
└ 💰 Coins: {coins:,}

━━━━━━━━━━━━━━━━━━━━━
📦 **Collection** ({collection_count})
━━━━━━━━━━━━━━━━━━━━━
├ 🟡 Legendary: {rarity_count['legendary']}
├ 🟣 Epic: {rarity_count['epic']}
├ 🔵 Rare: {rarity_count['rare']}
└ ⚪ Common: {rarity_count['common']}

━━━━━━━━━━━━━━━━━━━━━
🎮 **Game Stats**
━━━━━━━━━━━━━━━━━━━━━
├ ✅ Wins: {wins}
├ ❌ Losses: {losses}
└ 📈 Win Rate: {win_rate:.1f}%
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"Profile edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^view_lb$"))
async def view_leaderboard_callback(client: Client, callback: CallbackQuery):
    """View leaderboard callback"""
    debug(f"Leaderboard callback from {callback.from_user.first_name}")
    
    text = """
🏆 **Leaderboard**

━━━━━━━━━━━━━━━━━━━━━
Select a leaderboard to view:
━━━━━━━━━━━━━━━━━━━━━

📦 **Collection** - Most waifus
💰 **Coins** - Richest players
🎮 **Wins** - Best players
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Collection", callback_data="lb_collection"),
            InlineKeyboardButton("💰 Coins", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton("🎮 Wins", callback_data="lb_wins")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_start")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        debug(f"LB edit error: {e}")
    
    await callback.answer()
