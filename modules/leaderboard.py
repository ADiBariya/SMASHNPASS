# modules/leaderboard.py - Leaderboard Module

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from database import db
from helpers import Utils
from config import Config

# Help data for this module
HELP = {
    "name": "Leaderboard",
    "emoji": "🏆",
    "description": "View top players and rankings",
    "commands": {
        "leaderboard": "View leaderboard menu",
        "top": "View top collectors",
        "topwins": "View top winners",
        "toprich": "View richest players"
    }
}


def setup(app: Client):
    """Setup function called by loader"""
    
    @app.on_message(filters.command(["leaderboard", "lb", "top"], Config.CMD_PREFIX))
    async def leaderboard_command(client: Client, message: Message):
        """View leaderboard"""
        text = """
🏆 **Leaderboard**

Select a category to view:
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
                InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
            ],
            [
                InlineKeyboardButton("💰 Richest", callback_data="lb_rich"),
                InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
    
    
    @app.on_callback_query(filters.regex("^leaderboard_main$"))
    async def leaderboard_main_callback(client: Client, callback: CallbackQuery):
        """Handle leaderboard main callback"""
        text = """
🏆 **Leaderboard**

Select a category to view:
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
                InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
            ],
            [
                InlineKeyboardButton("💰 Richest", callback_data="lb_rich"),
                InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex("^lb_collectors$"))
    async def lb_collectors_callback(client: Client, callback: CallbackQuery):
        """Show top collectors"""
        top_users = db.get_top_collectors(10)
        
        text = "📦 **Top Collectors**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user_data.get("first_name") or user_data.get("username") or "Unknown"
            count = user_data.get("count", 0)
            
            text += f"{medal} **{name}** - {count} waifus\n"
        
        if not top_users:
            text += "_No data yet!_"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex("^lb_winners$"))
    async def lb_winners_callback(client: Client, callback: CallbackQuery):
        """Show top winners"""
        top_users = db.get_top_winners(10)
        
        text = "🎯 **Top Winners**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user_data.get("first_name") or user_data.get("username") or "Unknown"
            wins = user_data.get("total_wins", 0)
            
            text += f"{medal} **{name}** - {wins} wins\n"
        
        if not top_users:
            text += "_No data yet!_"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex("^lb_rich$"))
    async def lb_rich_callback(client: Client, callback: CallbackQuery):
        """Show richest players"""
        top_users = db.get_top_rich(10)
        
        text = "💰 **Richest Players**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user_data.get("first_name") or user_data.get("username") or "Unknown"
            coins = user_data.get("coins", 0)
            
            text += f"{medal} **{name}** - {coins:,} coins\n"
        
        if not top_users:
            text += "_No data yet!_"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex("^lb_global$"))
    async def lb_global_callback(client: Client, callback: CallbackQuery):
        """Show global stats"""
        stats = db.get_global_stats()
        
        text = f"""
📊 **Global Statistics**

👥 **Total Users:** {stats.get('total_users', 0):,}
📦 **Waifus Collected:** {stats.get('total_waifus_collected', 0):,}
💥 **Total Smashes:** {stats.get('total_smashes', 0):,}
👋 **Total Passes:** {stats.get('total_passes', 0):,}
"""
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_message(filters.command("topwins", Config.CMD_PREFIX))
    async def topwins_command(client: Client, message: Message):
        """Show top winners directly"""
        top_users = db.get_top_winners(10)
        
        text = "🎯 **Top Winners**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user_data.get("first_name") or user_data.get("username") or "Unknown"
            wins = user_data.get("total_wins", 0)
            
            text += f"{medal} **{name}** - {wins} wins\n"
        
        if not top_users:
            text += "_No data yet!_"
        
        await message.reply_text(text)
    
    
    @app.on_message(filters.command("toprich", Config.CMD_PREFIX))
    async def toprich_command(client: Client, message: Message):
        """Show richest players directly"""
        top_users = db.get_top_rich(10)
        
        text = "💰 **Richest Players**\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user_data.get("first_name") or user_data.get("username") or "Unknown"
            coins = user_data.get("coins", 0)
            
            text += f"{medal} **{name}** - {coins:,} coins\n"
        
        if not top_users:
            text += "_No data yet!_"
        
        await message.reply_text(text)