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

# Help data for this module
HELP = {
    "name": "Start",
    "emoji": "🏠",
    "description": "Bot start and info commands",
    "commands": {
        "start": "Start the bot and register",
        "ping": "Check bot latency",
        "stats": "View your statistics"
    }
}


def setup(app: Client):
    """Setup function called by loader"""
    
    @app.on_message(filters.command("start", config.CMD_PREFIX) & filters.private)
    async def start_private(client: Client, message: Message):
        """Handle /start command in private chat"""
        user = message.from_user
        
        # Get or create user in database
        db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        # Welcome message
        text = f"""
👋 **Welcome {user.first_name}!**

🎮 **Smash & Pass Waifu Bot**

Collect your favorite anime waifus by playing the Smash or Pass game!

🎯 **How to Play:**
• Use /smash to get a random waifu
• Choose **Smash** to try winning her
• Choose **Pass** to skip
• If you win, she joins your collection!

📦 **Features:**
• 50+ Beautiful Waifus
• Rarity System (Common to Legendary)
• Collection System
• Trading with friends
• Daily Rewards
• Leaderboards

**Ready to start? Use /smash now!**
"""
        
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
                    url=f"https://t.me/{Config.BOT_USERNAME}?startgroup=true")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
    
    
    @app.on_message(filters.command("start", Config.CMD_PREFIX) & filters.group)
    async def start_group(client: Client, message: Message):
        """Handle /start command in group"""
        user = message.from_user
        
        db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        text = f"""
🎮 **Smash & Pass Waifu Bot**

Hey {user.first_name}! Ready to collect waifus?

Use /smash to start playing!
Use /help for all commands.
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
                InlineKeyboardButton("📖 Help", callback_data="help_main")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
    
    
    @app.on_message(filters.command("ping", Config.CMD_PREFIX))
    async def ping_command(client: Client, message: Message):
        """Check bot latency"""
        import time
        
        start = time.time()
        msg = await message.reply_text("🏓 Pinging...")
        end = time.time()
        
        latency = (end - start) * 1000
        
        await msg.edit_text(f"🏓 **Pong!**\n⚡ Latency: `{latency:.2f}ms`")
    
    
    @app.on_message(filters.command("stats", Config.CMD_PREFIX))
    async def stats_command(client: Client, message: Message):
        """View user statistics"""
        user = message.from_user
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        
        collection_count = db.get_collection_count(user.id)
        
        text = f"""
📊 **Stats for {user.first_name}**

💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus Collected:** {collection_count}

🎮 **Game Stats:**
• Total Smashes: {user_data.get('total_smash', 0)}
• Total Passes: {user_data.get('total_pass', 0)}
• Wins: {user_data.get('total_wins', 0)} ✅
• Losses: {user_data.get('total_losses', 0)} ❌

📈 **Win Rate:** {(user_data.get('total_wins', 0) / max(user_data.get('total_smash', 1), 1) * 100):.1f}%
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
                InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_main")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
    
    
    @app.on_callback_query(filters.regex("^view_stats$"))
    async def view_stats_callback(client: Client, callback: CallbackQuery):
        """Handle stats button callback"""
        user = callback.from_user
        user_data = db.get_or_create_user(user.id, user.username, user.first_name)
        
        collection_count = db.get_collection_count(user.id)
        
        text = f"""
📊 **Stats for {user.first_name}**

💰 **Coins:** {user_data.get('coins', 0):,}
📦 **Waifus Collected:** {collection_count}

🎮 **Game Stats:**
• Total Smashes: {user_data.get('total_smash', 0)}
• Total Passes: {user_data.get('total_pass', 0)}
• Wins: {user_data.get('total_wins', 0)} ✅
• Losses: {user_data.get('total_losses', 0)} ❌

📈 **Win Rate:** {(user_data.get('total_wins', 0) / max(user_data.get('total_smash', 1), 1) * 100):.1f}%
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Collection", callback_data="view_collection"),
                InlineKeyboardButton("🔙 Back", callback_data="start_back")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex("^start_back$"))
    async def start_back_callback(client: Client, callback: CallbackQuery):
        """Handle back to start callback"""
        user = callback.from_user
        
        text = f"""
👋 **Welcome {user.first_name}!**

🎮 **Smash & Pass Waifu Bot**

Use the buttons below to navigate!
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
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
