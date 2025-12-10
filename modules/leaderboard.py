# modules/leaderboard.py - Direct Command Registration (No Setup Function)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
import config
import logging

logger = logging.getLogger(__name__)

__MODULE__ = "Leaderboard"
__HELP__ = """
🏆 **Leaderboard Commands**

• `/leaderboard` or `/lb` - View leaderboard menu
• `/top` - View top collectors
• `/topwins` - View top winners
• `/toprich` - View richest players
"""


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def get_user_name(user_id: int, user_data: dict = None) -> str:
    """Get user's display name"""
    if user_data:
        if user_data.get("display_name"):
            return user_data["display_name"]
        if user_data.get("first_name"):
            return user_data["first_name"]
        if user_data.get("username"):
            return user_data["username"]
    return f"User {user_id}"


def get_top_collectors_direct(limit: int = 10):
    """Get top collectors by directly querying database"""
    try:
        all_users = list(db.users.find({}))
        user_collection_data = []
        
        for user in all_users:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            collection = user.get("collection", [])
            collection_count = len(collection)
            
            if collection_count > 0:
                user_collection_data.append({
                    "user_id": user_id,
                    "first_name": user.get("first_name", "Unknown"),
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "collection_count": collection_count
                })
        
        user_collection_data.sort(key=lambda x: x["collection_count"], reverse=True)
        return user_collection_data[:limit]
    except Exception as e:
        logger.error(f"Error getting top collectors: {e}")
        return []


def get_top_winners_direct(limit: int = 10):
    """Get top winners by directly querying database"""
    try:
        top_users = list(db.users.find({}).sort("total_wins", -1).limit(limit))
        return top_users
    except Exception as e:
        logger.error(f"Error getting top winners: {e}")
        return []


def get_top_rich_direct(limit: int = 10):
    """Get richest players by directly querying database"""
    try:
        top_users = list(db.users.find({}).sort("coins", -1).limit(limit))
        return top_users
    except Exception as e:
        logger.error(f"Error getting top rich: {e}")
        return []


def get_global_stats_direct():
    """Get global statistics directly from database"""
    try:
        total_users = db.users.count_documents({})
        all_users = list(db.users.find({}))
        
        total_waifus = 0
        total_smashes = 0
        total_passes = 0
        
        for user in all_users:
            collection = user.get("collection", [])
            total_waifus += len(collection)
            total_smashes += user.get("total_smash", 0)
            total_passes += user.get("total_pass", 0)
        
        return {
            "total_users": total_users,
            "total_waifus_collected": total_waifus,
            "total_smashes": total_smashes,
            "total_passes": total_passes
        }
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        return {
            "total_users": 0,
            "total_waifus_collected": 0,
            "total_smashes": 0,
            "total_passes": 0
        }


# ═══════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["leaderboard", "lb"], config.COMMAND_PREFIX))
async def leaderboard_command(client: Client, message: Message):
    """Show leaderboard main menu"""
    text = """
🏆 **LEADERBOARD MENU**
━━━━━━━━━━━━━━━━━━━━━━━━

Choose a category to view rankings!

💖 *Compete to be the best!*
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
            InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
        ],
        [
            InlineKeyboardButton("💰 Richest Players", callback_data="lb_rich"),
            InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


@Client.on_message(filters.command("top", config.COMMAND_PREFIX))
async def top_command(client: Client, message: Message):
    """Show top collectors directly"""
    top_users = get_top_collectors_direct(10)
    
    text = "📦 **TOP WAIFU COLLECTORS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No collectors yet! Be the first!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            count = user_data.get("collection_count", 0)
            
            text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


@Client.on_message(filters.command("topwins", config.COMMAND_PREFIX))
async def topwins_command(client: Client, message: Message):
    """Show top winners directly"""
    top_users = get_top_winners_direct(10)
    
    text = "🎯 **TOP BATTLE CHAMPIONS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No winners yet! Start battling!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            wins = user_data.get("total_wins", 0)
            
            text += f"{medal} **{name}** — {wins} wins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


@Client.on_message(filters.command("toprich", config.COMMAND_PREFIX))
async def toprich_command(client: Client, message: Message):
    """Show richest players directly"""
    top_users = get_top_rich_direct(10)
    
    text = "💰 **TOP COIN MASTERS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No rich players yet! Earn coins!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            coins = user_data.get("coins", 0)
            
            text += f"{medal} **{name}** — {coins:,} coins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^lb_collectors$"))
async def lb_collectors_callback(client: Client, callback: CallbackQuery):
    """Show top collectors"""
    await callback.answer("Loading...")
    
    top_users = get_top_collectors_direct(10)
    
    text = "📦 **TOP WAIFU COLLECTORS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No collectors yet! Be the first!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            count = user_data.get("collection_count", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {count} waifus ✨\n"
            else:
                text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex("^lb_winners$"))
async def lb_winners_callback(client: Client, callback: CallbackQuery):
    """Show top winners"""
    await callback.answer("Loading...")
    
    top_users = get_top_winners_direct(10)
    
    text = "🎯 **TOP BATTLE CHAMPIONS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No winners yet! Start battling!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            wins = user_data.get("total_wins", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {wins} wins ⚔️\n"
            else:
                text += f"{medal} **{name}** — {wins} wins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex("^lb_rich$"))
async def lb_rich_callback(client: Client, callback: CallbackQuery):
    """Show richest players"""
    await callback.answer("Loading...")
    
    top_users = get_top_rich_direct(10)
    
    text = "💰 **TOP COIN MASTERS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No rich players yet! Earn coins!*"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(user_id, user_data)
            coins = user_data.get("coins", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {coins:,} coins 💎\n"
            else:
                text += f"{medal} **{name}** — {coins:,} coins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex("^lb_global$"))
async def lb_global_callback(client: Client, callback: CallbackQuery):
    """Show global statistics"""
    await callback.answer("Loading...")
    
    stats = get_global_stats_direct()
    
    text = f"""
📊 **GLOBAL STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

👥 **Total Users:** {stats['total_users']:,}
📦 **Waifus Collected:** {stats['total_waifus_collected']:,}
💥 **Total Smashes:** {stats['total_smashes']:,}
👋 **Total Passes:** {stats['total_passes']:,}

━━━━━━━━━━━━━━━━━━━━━━━━

*Keep playing to improve these numbers!* 💖
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex("^lb_main$"))
async def lb_main_callback(client: Client, callback: CallbackQuery):
    """Back to main leaderboard menu"""
    await callback.answer()
    
    text = """
🏆 **LEADERBOARD MENU**
━━━━━━━━━━━━━━━━━━━━━━━━

Choose a category to view rankings!

💖 *Compete to be the best!*
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
            InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
        ],
        [
            InlineKeyboardButton("💰 Richest Players", callback_data="lb_rich"),
            InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
