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
#  /start Command - Direct decorator (no setup wrapper)
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
    """Check bot latency"""
    import time
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    latency = (end - start) * 1000
    await msg.edit_text(f"🏓 **Pong!**\n⚡ Latency: `{latency:.2f}ms`")


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
    text = """
📖 **Help Menu**

🎮 /smash - Start game
📦 /collection - Your waifus
📊 /stats - Statistics
💰 /daily - Daily reward
🏓 /ping - Bot latency
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
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
