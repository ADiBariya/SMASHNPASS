from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from database import db
import config
import logging

logger = logging.getLogger(__name__)

async def get_user_name(client: Client, user_id: int, user_data: dict = None) -> str:
    """Get user display name with fallback"""
    if user_data:
        if user_data.get("display_name"):
            return user_data["display_name"]
        if user_data.get("first_name"):
            return user_data["first_name"]
    
    try:
        user = await client.get_users(user_id)
        return user.first_name or "Unknown"
    except:
        return "Unknown"

__MODULE__ = "Leaderboard"
__HELP__ = """
🏆 **Leaderboard Commands**

• `/leaderboard` or `/lb` - View leaderboard menu
• `/top` - View top collectors
• `/topwins` - View top winners
• `/toprich` - View richest players
"""

# Helper to get rank emoji
def get_rank_emoji(rank):
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return f"#{rank}"

@Client.on_message(filters.command(["top", "leaderboard", "lb"], config.COMMAND_PREFIX))
async def leaderboard_menu(client: Client, message: Message):
    """Show leaderboard menu"""
    text = "🏆 **Global Leaderboard**\n\nChoose a category:"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collection"),
            InlineKeyboardButton("💰 Top Rich", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton("🎮 Top Wins", callback_data="lb_wins"),
            InlineKeyboardButton("📊 Stats", callback_data="lb_global")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^lb_main$"))
async def back_to_lb_main(client: Client, callback: CallbackQuery):
    """Back to main leaderboard menu"""
    text = "🏆 **Global Leaderboard**\n\nChoose a category:"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collection"),
            InlineKeyboardButton("💰 Top Rich", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton("🎮 Top Wins", callback_data="lb_wins"),
            InlineKeyboardButton("📊 Stats", callback_data="lb_global")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^lb_collection$"))
async def lb_collectors_callback(client: Client, callback: CallbackQuery):
    """Show top collectors"""
    await callback.answer("Loading top collectors...")
    
    # Use optimized db method
    top_users = db.get_top_collectors(10)
    
    text = "📦 **TOP WAIFU COLLECTORS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No collectors yet! Be the first!*\\n"
        text += "\\n💡 Use smash command to collect waifus!"
    else:
        for i, user_data in enumerate(top_users, 1):
            medal = get_rank_emoji(i)
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            count = user_data.get("count", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {count} waifus ✨\n"
            else:
                text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Show user rank if not in top 10
    user_id = callback.from_user.id
    user_in_top = any(u.get('user_id') == user_id for u in top_users)
    
    if not user_in_top:
        user_count = db.get_collection_count(user_id)
        if user_count > 0:
            user_rank = db.get_user_rank(user_id, "collection")
            text += f"\n\n👤 **Your Rank:** #{user_rank} ({user_count} waifus)"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^lb_coins$"))
async def lb_coins_callback(client: Client, callback: CallbackQuery):
    """Show richest users"""
    await callback.answer("Loading richest users...")
    
    top_users = list(db.users.find({"coins": {"$gt": 0}}).sort("coins", -1).limit(10))
    
    text = "💰 **WEALTH LEADERBOARD**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No data available!*"
    else:
        for i, user in enumerate(top_users, 1):
            medal = get_rank_emoji(i)
            name = user.get("display_name") or user.get("first_name", "Unknown")
            coins = user.get("coins", 0)
            
            text += f"{medal} **{name}** — {coins:,} coins\n"
            
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^lb_wins$"))
async def lb_wins_callback(client: Client, callback: CallbackQuery):
    """Show top winners"""
    await callback.answer("Loading top winners...")
    
    # Check both wins and total_wins fields just in case
    top_users = list(db.users.find({
        "$or": [{"wins": {"$gt": 0}}, {"total_wins": {"$gt": 0}}]
    }).sort("total_wins", -1).limit(10))
    
    text = "🎮 **TOP PLAYERS (WINS)**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No matches recorded!*"
    else:
        for i, user in enumerate(top_users, 1):
            medal = get_rank_emoji(i)
            name = user.get("display_name") or user.get("first_name", "Unknown")
            wins = user.get("total_wins", user.get("wins", 0))
            
            text += f"{medal} **{name}** — {wins} wins\n"
            
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^lb_global$"))
async def lb_global_callback(client: Client, callback: CallbackQuery):
    """Show global bot stats"""
    stats = db.get_global_stats()
    
    text = f"""
📊 **GLOBAL STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

👥 **Total Users:** `{stats['total_users']}`
📦 **Waifus Collected:** `{stats['total_waifus_collected']}`
✅ **Total Smashes:** `{stats['total_smashes']}`
❌ **Total Passes:** `{stats['total_passes']}`

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


# Direct commands (Aliases)

@Client.on_message(filters.command("topwins", config.COMMAND_PREFIX))
async def topwins_command(client: Client, message: Message):
    # Reuse callback logic by mocking it or just copy code. 
    # Copying code is safer for message context.
    
    top_users = list(db.users.find({
        "$or": [{"wins": {"$gt": 0}}, {"total_wins": {"$gt": 0}}]
    }).sort("total_wins", -1).limit(10))
    
    text = "🎮 **TOP PLAYERS (WINS)**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No matches recorded!*"
    else:
        for i, user in enumerate(top_users, 1):
            medal = get_rank_emoji(i)
            name = user.get("display_name") or user.get("first_name", "Unknown")
            wins = user.get("total_wins", user.get("wins", 0))
            
            text += f"{medal} **{name}** — {wins} wins\n"
            
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    await message.reply_text(text)


@Client.on_message(filters.command("toprich", config.COMMAND_PREFIX))
async def toprich_command(client: Client, message: Message):
    top_users = list(db.users.find({"coins": {"$gt": 0}}).sort("coins", -1).limit(10))
    
    text = "💰 **WEALTH LEADERBOARD**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No data available!*"
    else:
        for i, user in enumerate(top_users, 1):
            medal = get_rank_emoji(i)
            name = user.get("display_name") or user.get("first_name", "Unknown")
            coins = user.get("coins", 0)
            
            text += f"{medal} **{name}** — {coins:,} coins\n"
            
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    await message.reply_text(text)

print("LEADERBOARD MODULE LOADED SUCCESSFULLY")

