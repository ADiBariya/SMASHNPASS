# modules/leaderboard.py - Fixed Leaderboard Module

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
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

async def get_user_name(client: Client, user_id: int, user_data: dict = None) -> str:
    """Get user's display name"""
    try:
        # Check user_data first
        if user_data:
            if user_data.get("display_name"):
                return str(user_data["display_name"])[:20]
            if user_data.get("first_name"):
                return str(user_data["first_name"])[:20]
            if user_data.get("username"):
                return f"@{user_data['username']}"[:20]
        
        # Try to fetch from Telegram
        try:
            user = await client.get_users(user_id)
            if user:
                name = user.first_name or user.username or f"User {user_id}"
                # Update database
                try:
                    db.users.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "first_name": user.first_name,
                            "username": user.username
                        }},
                        upsert=True
                    )
                except:
                    pass
                return str(name)[:20]
        except Exception as e:
            logger.debug(f"Could not fetch user {user_id}: {e}")
        
        return f"User {user_id}"
    except Exception as e:
        logger.error(f"Error in get_user_name: {e}")
        return f"User {user_id}"


def get_top_collectors_direct(limit: int = 10):
    """Get top collectors by directly querying database"""
    try:
        # Method 1: Check if collection is stored in users collection
        all_users = list(db.users.find({}))
        user_collection_data = []
        
        for user in all_users:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            # Try embedded collection first
            collection = user.get("collection", [])
            collection_count = len(collection) if isinstance(collection, list) else 0
            
            # If no embedded collection, check collections collection
            if collection_count == 0:
                try:
                    collection_count = db.collections.count_documents({"user_id": user_id})
                except:
                    pass
            
            if collection_count > 0:
                user_collection_data.append({
                    "user_id": user_id,
                    "first_name": user.get("first_name"),
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "collection_count": collection_count
                })
        
        # Sort by collection count
        user_collection_data.sort(key=lambda x: x["collection_count"], reverse=True)
        
        logger.info(f"Found {len(user_collection_data)} collectors")
        return user_collection_data[:limit]
        
    except Exception as e:
        logger.error(f"Error getting top collectors: {e}")
        return []


def get_top_winners_direct(limit: int = 10):
    """Get top winners by directly querying database"""
    try:
        # Find users with wins > 0, sorted by total_wins
        top_users = list(
            db.users.find(
                {"total_wins": {"$gt": 0}}
            ).sort("total_wins", -1).limit(limit)
        )
        
        logger.info(f"Found {len(top_users)} winners")
        return top_users
        
    except Exception as e:
        logger.error(f"Error getting top winners: {e}")
        return []


def get_top_rich_direct(limit: int = 10):
    """Get richest players by directly querying database"""
    try:
        # Find users with coins > 0, sorted by coins
        top_users = list(
            db.users.find(
                {"coins": {"$gt": 0}}
            ).sort("coins", -1).limit(limit)
        )
        
        logger.info(f"Found {len(top_users)} rich users")
        return top_users
        
    except Exception as e:
        logger.error(f"Error getting top rich: {e}")
        return []


def get_global_stats_direct():
    """Get global statistics directly from database"""
    try:
        total_users = db.users.count_documents({})
        
        # Calculate totals
        all_users = list(db.users.find({}))
        
        total_waifus = 0
        total_smashes = 0
        total_passes = 0
        
        for user in all_users:
            # Count embedded collection
            collection = user.get("collection", [])
            if isinstance(collection, list):
                total_waifus += len(collection)
            
            total_smashes += user.get("total_smash", 0) or 0
            total_passes += user.get("total_pass", 0) or 0
        
        # Also count from collections collection if exists
        try:
            collections_count = db.collections.count_documents({})
            if collections_count > total_waifus:
                total_waifus = collections_count
        except:
            pass
        
        stats = {
            "total_users": total_users,
            "total_waifus_collected": total_waifus,
            "total_smashes": total_smashes,
            "total_passes": total_passes
        }
        
        logger.info(f"Global stats: {stats}")
        return stats
        
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


async def top_command(client: Client, message: Message):
    """Show top collectors directly"""
    await message.reply_text("🔄 Loading top collectors...")
    
    top_users = get_top_collectors_direct(10)
    
    text = "📦 **TOP WAIFU COLLECTORS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No collectors yet! Be the first!*\n"
        text += "\n💡 Use smash command to collect waifus!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            count = user_data.get("collection_count", 0)
            
            if i == 1:
                text += f"{medal} **{name}** — {count} waifus 💘🔥\n"
            elif i == 2:
                text += f"{medal} **{name}** — {count} waifus 💖✨\n"
            elif i == 3:
                text += f"{medal} **{name}** — {count} waifus 💕🌟\n"
            else:
                text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


async def topwins_command(client: Client, message: Message):
    """Show top winners directly"""
    top_users = get_top_winners_direct(10)
    
    text = "🎯 **TOP BATTLE CHAMPIONS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No winners yet! Start battling!*\n"
        text += "\n💡 Use battle command to compete!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            wins = user_data.get("total_wins", 0)
            
            if i == 1:
                text += f"{medal} **{name}** — {wins} wins ⚔️💥\n"
            elif i == 2:
                text += f"{medal} **{name}** — {wins} wins ⚔️🔥\n"
            elif i == 3:
                text += f"{medal} **{name}** — {wins} wins ⚔️✨\n"
            else:
                text += f"{medal} **{name}** — {wins} wins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


async def toprich_command(client: Client, message: Message):
    """Show richest players directly"""
    top_users = get_top_rich_direct(10)
    
    text = "💰 **TOP COIN MASTERS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No rich players yet! Earn coins!*\n"
        text += "\n💡 Use /daily to claim free coins!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            coins = user_data.get("coins", 0)
            
            if i == 1:
                text += f"{medal} **{name}** — {coins:,} coins 💰💎\n"
            elif i == 2:
                text += f"{medal} **{name}** — {coins:,} coins 💰✨\n"
            elif i == 3:
                text += f"{medal} **{name}** — {coins:,} coins 💰🔥\n"
            else:
                text += f"{medal} **{name}** — {coins:,} coins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply_text(text)


async def lb_debug_command(client: Client, message: Message):
    """Debug command to check database status"""
    try:
        # Count documents
        users_count = db.users.count_documents({})
        collections_count = db.collections.count_documents({})
        
        # Sample data
        sample_user = db.users.find_one({})
        sample_collection = db.collections.find_one({})
        
        # Users with data
        users_with_coins = db.users.count_documents({"coins": {"$gt": 0}})
        users_with_wins = db.users.count_documents({"total_wins": {"$gt": 0}})
        
        text = "🔧 **LEADERBOARD DEBUG**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"👥 Total Users: {users_count}\n"
        text += f"📦 Collections Entries: {collections_count}\n"
        text += f"💰 Users with Coins: {users_with_coins}\n"
        text += f"🏆 Users with Wins: {users_with_wins}\n\n"
        
        if sample_user:
            text += "**Sample User Fields:**\n"
            fields = list(sample_user.keys())[:10]
            text += f"`{', '.join(fields)}`\n\n"
            
            # Check collection field
            if "collection" in sample_user:
                coll = sample_user.get("collection", [])
                text += f"📦 Embedded collection: {len(coll) if isinstance(coll, list) else 'N/A'} items\n"
        
        if sample_collection:
            text += "\n**Sample Collection Fields:**\n"
            fields = list(sample_collection.keys())[:10]
            text += f"`{', '.join(fields)}`\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ Debug error: {e}")


# ═══════════════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def lb_collectors_callback(client: Client, callback: CallbackQuery):
    """Show top collectors"""
    await callback.answer("Loading collectors...")
    
    top_users = get_top_collectors_direct(10)
    
    text = "📦 **TOP WAIFU COLLECTORS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No collectors yet! Be the first!*\n"
        text += "\n💡 Collect waifus to appear here!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            count = user_data.get("collection_count", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {count} waifus ✨\n"
            else:
                text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error editing message: {e}")


async def lb_winners_callback(client: Client, callback: CallbackQuery):
    """Show top winners"""
    await callback.answer("Loading winners...")
    
    top_users = get_top_winners_direct(10)
    
    text = "🎯 **TOP BATTLE CHAMPIONS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No winners yet! Start battling!*\n"
        text += "\n💡 Win battles to appear here!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            wins = user_data.get("total_wins", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {wins} wins ⚔️\n"
            else:
                text += f"{medal} **{name}** — {wins} wins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error editing message: {e}")


async def lb_rich_callback(client: Client, callback: CallbackQuery):
    """Show richest players"""
    await callback.answer("Loading rich players...")
    
    top_users = get_top_rich_direct(10)
    
    text = "💰 **TOP COIN MASTERS**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not top_users:
        text += "*No rich players yet! Earn coins!*\n"
        text += "\n💡 Earn coins to appear here!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            
            user_id = user_data.get("user_id")
            name = await get_user_name(client, user_id, user_data)
            coins = user_data.get("coins", 0)
            
            if i <= 3:
                text += f"{medal} **{name}** — {coins:,} coins 💎\n"
            else:
                text += f"{medal} **{name}** — {coins:,} coins\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="lb_main")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error editing message: {e}")


async def lb_global_callback(client: Client, callback: CallbackQuery):
    """Show global statistics"""
    await callback.answer("Loading stats...")
    
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
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error editing message: {e}")


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
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error editing message: {e}")


# ═══════════════════════════════════════════════════════════════════
#  SETUP FUNCTION - Required to register handlers
# ═══════════════════════════════════════════════════════════════════

def setup(app: Client):
    """Register all leaderboard handlers"""
    
    # Command handlers
    app.add_handler(MessageHandler(
        leaderboard_command,
        filters.command(["leaderboard", "lb"], config.COMMAND_PREFIX)
    ))
    
    app.add_handler(MessageHandler(
        top_command,
        filters.command(["top", "topcollectors"], config.COMMAND_PREFIX)
    ))
    
    app.add_handler(MessageHandler(
        topwins_command,
        filters.command("topwins", config.COMMAND_PREFIX)
    ))
    
    app.add_handler(MessageHandler(
        toprich_command,
        filters.command("toprich", config.COMMAND_PREFIX)
    ))
    
    # Debug command (owner only)
    app.add_handler(MessageHandler(
        lb_debug_command,
        filters.command("lbdebug", config.COMMAND_PREFIX) & filters.user(config.OWNER_ID)
    ))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(
        lb_collectors_callback,
        filters.regex("^lb_collectors$")
    ))
    
    app.add_handler(CallbackQueryHandler(
        lb_winners_callback,
        filters.regex("^lb_winners$")
    ))
    
    app.add_handler(CallbackQueryHandler(
        lb_rich_callback,
        filters.regex("^lb_rich$")
    ))
    
    app.add_handler(CallbackQueryHandler(
        lb_global_callback,
        filters.regex("^lb_global$")
    ))
    
    app.add_handler(CallbackQueryHandler(
        lb_main_callback,
        filters.regex("^lb_main$")
    ))
    
    logger.info("✅ Leaderboard module loaded successfully!")
