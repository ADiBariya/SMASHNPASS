# modules/start.py - Start Command Module

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from database import db
import config
import time 
from datetime import datetime

#track time 
BOT_START_TIME = datetime.now()

def get_formatted_uptime():
    """Calculate and return nicely formatted bot uptime"""
    uptime_delta = datetime.now() - BOT_START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Build uptime string with only non-zero values (clean format)
   
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


# ═══════════════════════════════════════════════════════════════════
#  /start Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("start", config.COMMAND_PREFIX))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    # Database
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except Exception as e:
        print(f"⚠️ DB error: {e}")
    
    # Welcome text
    text = f"""
👋 **Welcome {user.first_name}!**

🎮 **Smash or Pass Waifu Game**

Collect your favorite anime waifus!

🎯 **How to Play:**
• Use /smash to get a random waifu
• Choose **💥 Smash** to try winning her
• Choose **👋 Pass** to skip
• If you win, she joins your collection!

✨ **Ready? Tap Play Now!**
"""
    
    # Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("📖 Help", callback_data="help_main"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
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
    except Exception as e:
        print(f"⚠️ Image failed: {e}")
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
    
    # Calculate metrics
    latency = (end - start) * 1000
    uptime = get_formatted_uptime()
    
    await msg.edit_text(
        f"🏓 **Pong!**\n"
        f"⚡ Latency: `{latency:.2f}ms`\n"
        f"⏳ Uptime: `{uptime}`"
    )

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

💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus:** {collection_count}

🎮 **Game Stats:**
├ Smashes: {total_smash}
├ Passes: {user_data.get('total_pass', 0)}
├ Wins: {total_wins} ✅
└ Losses: {user_data.get('total_losses', 0)} ❌

📈 **Win Rate:** {win_rate:.1f}%
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
            InlineKeyboardButton("🎮 Play", callback_data="play_smash")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  Callbacks
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^view_stats$"))
async def view_stats_callback(client: Client, callback: CallbackQuery):
    """View stats callback"""
    user = callback.from_user
    
    try:
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        collection_count = db.get_collection_count(user.id)
    except:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    total_smash = user_data.get('total_smash', 0)
    total_wins = user_data.get('total_wins', 0)
    win_rate = (total_wins / total_smash * 100) if total_smash > 0 else 0
    
    text = f"""
📊 **Stats for {user.first_name}**

💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus:** {collection_count}
📈 **Win Rate:** {win_rate:.1f}%
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back", callback_data="start_back")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex("^start_back$"))
async def start_back_callback(client: Client, callback: CallbackQuery):
    """Back to start callback"""
    user = callback.from_user
    
    text = f"""
👋 **Welcome {user.first_name}!**

🎮 **Smash or Pass Waifu Game**

✨ Use the buttons below!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ],
        [
            InlineKeyboardButton("📖 Help", callback_data="help_main"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex("^help_main$"))
async def help_main_callback(client: Client, callback: CallbackQuery):
    """Help menu callback"""
    print(f"📖 [HELP] Callback received from {callback.from_user.first_name}")
    
    text = """
📖 **Help Menu**

🎮 **Game Commands:**
├ /smash - Start a new game
├ /collection - View your waifus
├ /stats - Your statistics
└ /daily - Claim daily reward

💰 **Economy:**
├ /balance - Check coins
├ /shop - Visit shop
└ /gift - Gift waifu/coins

🏆 **Others:**
├ /leaderboard - Top players
├ /profile - Your profile
└ /ping - Bot latency

**Tip:** Legendary waifus are rare but powerful!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
            InlineKeyboardButton("🔙 Back", callback_data="start_back")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
        print("✅ [HELP] Menu sent!")
    except Exception as e:
        print(f"❌ [HELP] Error: {e}")
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
#  📦 View Collection Callback (Add here if not in collection.py)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^view_collection$"))
async def view_collection_callback(client: Client, callback: CallbackQuery):
    """View collection callback"""
    user = callback.from_user
    
    print(f"📦 [COLLECTION] Callback from {user.first_name}")
    
    try:
        collection = db.get_user_collection(user.id)
    except Exception as e:
        print(f"❌ [COLLECTION] DB Error: {e}")
        await callback.answer("❌ Database error!", show_alert=True)
        return
    
    if not collection:
        text = f"""
📦 **{user.first_name}'s Collection**

😢 **Your collection is empty!**

Play /smash to win waifus and add them to your collection!
"""
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Play Now", callback_data="play_smash"),
                InlineKeyboardButton("🔙 Back", callback_data="start_back")
            ]
        ])
    else:
        # Show first 5 waifus
        text = f"""
📦 **{user.first_name}'s Collection**

📊 **Total Waifus:** {len(collection)}

"""
        # Get rarity emoji helper
        rarity_emojis = {
            "common": "⚪",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }
        
        for i, waifu in enumerate(collection[:5], 1):
            rarity = waifu.get("waifu_rarity") or waifu.get("rarity", "common")
            emoji = rarity_emojis.get(rarity, "⚪")
            name = waifu.get("waifu_name") or waifu.get("name", "Unknown")
            power = waifu.get("waifu_power") or waifu.get("power", 0)
            text += f"{i}. {emoji} **{name}** (⚔️ {power})\n"
        
        if len(collection) > 5:
            text += f"\n... and {len(collection) - 5} more!"
        
        text += "\n\nUse /collection for full list!"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Play More", callback_data="play_smash"),
                InlineKeyboardButton("🔙 Back", callback_data="start_back")
            ]
        ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
        print("✅ [COLLECTION] Sent!")
    except Exception as e:
        print(f"❌ [COLLECTION] Edit error: {e}")
    
    await callback.answer()
