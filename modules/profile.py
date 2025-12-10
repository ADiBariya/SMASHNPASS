# modules/profile.py - Complete Profile & Leaderboard System

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.enums import ParseMode
from database import db
import config
import logging

logger = logging.getLogger(__name__)

__MODULE__ = "Profile & Leaderboard"
__HELP__ = """
👤 **Profile Commands**
• `/profile` or `/p` - View your profile
• `/profile @user` - View someone's profile
• `/rename <name>` - Set display name

🏆 **Leaderboard Commands**
• `/leaderboard` or `/lb` - View leaderboard menu
• `/top` - View top collectors
• `/topwins` - View top winners
• `/toprich` - View richest players
"""

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        logger.info(f"[PROFILE] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity"""
    return {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(rarity).lower(), "⚪")


def get_rank_emoji(rank: int) -> str:
    """Get medal emoji for rank"""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return f"#{rank}"


def calculate_value(waifus: list) -> int:
    """Calculate total value based on rarity counts"""
    values = {
        "common": 10,
        "rare": 50,
        "epic": 100,
        "legendary": 250
    }
    total = 0
    for w in waifus:
        r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
        total += values.get(r, 10)
    return total


def get_title(wins: int, collection_count: int) -> str:
    """Get user title based on wins and collection"""
    if wins >= 500 or collection_count >= 100:
        return "👑 Legendary Hunter"
    elif wins >= 250 or collection_count >= 50:
        return "⚔️ Elite Collector"
    elif wins >= 100 or collection_count >= 25:
        return "🎯 Pro Hunter"
    elif wins >= 50 or collection_count >= 10:
        return "⭐ Rising Star"
    elif wins >= 10:
        return "🎮 Active Player"
    else:
        return "🌱 Novice"


def get_user_collection(user_id: int) -> list:
    """Get user's FULL collection from database"""
    try:
        # Method 1: Direct from users collection (embedded)
        user_doc = db.users.find_one({"user_id": user_id})
        if user_doc:
            collection = user_doc.get("collection", [])
            if isinstance(collection, list) and len(collection) > 0:
                debug(f"Found {len(collection)} waifus embedded for user {user_id}")
                return collection
        
        # Method 2: From separate collections collection
        try:
            if hasattr(db, 'collections'):
                collection_cursor = db.collections.find({"user_id": user_id})
                collection = list(collection_cursor)
                if collection:
                    debug(f"Found {len(collection)} waifus in collections for user {user_id}")
                    return collection
        except Exception as e:
            debug(f"Collections query error: {e}")
        
        # Method 3: Try database methods
        if hasattr(db, 'get_user_collection'):
            collection = db.get_user_collection(user_id)
            if collection:
                debug(f"Found {len(collection)} waifus via get_user_collection")
                return collection
        
        if hasattr(db, 'get_full_collection'):
            collection = db.get_full_collection(user_id)
            if collection:
                debug(f"Found {len(collection)} waifus via get_full_collection")
                return collection
        
        return []
        
    except Exception as e:
        debug(f"Error fetching collection for {user_id}: {e}")
        return []


def get_user_stats(user_id: int) -> dict:
    """Get comprehensive user statistics"""
    try:
        user_data = db.get_user(user_id) if hasattr(db, 'get_user') else None
        if not user_data:
            user_data = db.users.find_one({"user_id": user_id}) or {}
        
        # Get FULL collection
        collection = get_user_collection(user_id)
        
        # Count by rarity
        rarity_count = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        for w in collection:
            r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
            if r in rarity_count:
                rarity_count[r] += 1
        
        debug(f"User {user_id}: {len(collection)} waifus, rarities: {rarity_count}")
        
        return {
            "user_data": user_data,
            "collection": collection,
            "rarity_count": rarity_count,
            "total_value": calculate_value(collection)
        }
    except Exception as e:
        debug(f"Error getting stats: {e}")
        return None


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
            debug(f"Could not fetch user {user_id}: {e}")
        
        return f"User {user_id}"
    except Exception as e:
        debug(f"Error in get_user_name: {e}")
        return f"User {user_id}"


def get_all_users_with_stats() -> list:
    """Get all users with their collection and stats data"""
    try:
        all_users = list(db.users.find({}))
        users_with_stats = []
        
        for user in all_users:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            # Get collection
            collection = get_user_collection(user_id)
            
            # Add calculated fields
            user_stats = user.copy()
            user_stats["_collection"] = collection
            user_stats["_collection_count"] = len(collection)
            user_stats["_collection_value"] = calculate_value(collection)
            user_stats["_net_worth"] = user.get("coins", 0) + calculate_value(collection)
            
            users_with_stats.append(user_stats)
        
        return users_with_stats
    except Exception as e:
        debug(f"Error getting users with stats: {e}")
        return []


def get_top_collectors(limit: int = 10) -> list:
    """Get top collectors by collection count"""
    try:
        users = get_all_users_with_stats()
        
        # Filter users with collections
        collectors = [u for u in users if u.get("_collection_count", 0) > 0]
        
        # Sort by collection count
        collectors.sort(key=lambda x: x.get("_collection_count", 0), reverse=True)
        
        debug(f"Found {len(collectors)} collectors")
        return collectors[:limit]
        
    except Exception as e:
        debug(f"Error getting top collectors: {e}")
        return []


def get_top_winners(limit: int = 10) -> list:
    """Get top winners by total wins"""
    try:
        top_users = list(
            db.users.find(
                {"total_wins": {"$gt": 0}}
            ).sort("total_wins", -1).limit(limit)
        )
        
        debug(f"Found {len(top_users)} winners")
        return top_users
        
    except Exception as e:
        debug(f"Error getting top winners: {e}")
        return []


def get_top_rich(limit: int = 10) -> list:
    """Get richest players by coins"""
    try:
        top_users = list(
            db.users.find(
                {"coins": {"$gt": 0}}
            ).sort("coins", -1).limit(limit)
        )
        
        debug(f"Found {len(top_users)} rich users")
        return top_users
        
    except Exception as e:
        debug(f"Error getting top rich: {e}")
        return []


def get_global_stats() -> dict:
    """Get global statistics"""
    try:
        total_users = db.users.count_documents({})
        
        # Calculate totals
        all_users = list(db.users.find({}))
        
        total_waifus = 0
        total_smashes = 0
        total_passes = 0
        total_coins = 0
        
        for user in all_users:
            # Count collection
            collection = get_user_collection(user.get("user_id", 0))
            total_waifus += len(collection)
            
            total_smashes += user.get("total_smash", 0) or user.get("total_wins", 0) or 0
            total_passes += user.get("total_pass", 0) or user.get("total_losses", 0) or 0
            total_coins += user.get("coins", 0) or 0
        
        stats = {
            "total_users": total_users,
            "total_waifus": total_waifus,
            "total_smashes": total_smashes,
            "total_passes": total_passes,
            "total_coins": total_coins
        }
        
        debug(f"Global stats: {stats}")
        return stats
        
    except Exception as e:
        debug(f"Error getting global stats: {e}")
        return {
            "total_users": 0,
            "total_waifus": 0,
            "total_smashes": 0,
            "total_passes": 0,
            "total_coins": 0
        }


def get_user_rank(user_id: int) -> int:
    """Get user's global rank by net worth"""
    try:
        users = get_all_users_with_stats()
        
        # Sort by net worth
        users.sort(key=lambda x: x.get("_net_worth", 0), reverse=True)
        
        for i, u in enumerate(users, 1):
            if u.get("user_id") == user_id:
                return i
        
        return 0
    except:
        return 0


# ═══════════════════════════════════════════════════════════════════
#  PROFILE COMMANDS
# ═══════════════════════════════════════════════════════════════════

async def profile_command(client: Client, message: Message):
    """View user profile - Professional layout"""
    debug(f"Profile command from {message.from_user.id}")
    
    # Get target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            await message.reply_text("❌ **User not found!**")
            return
    else:
        target = message.from_user
    
    debug(f"Viewing profile for {target.id}")
    
    # Get stats
    stats = get_user_stats(target.id)
    if not stats:
        await message.reply_text("❌ **Database error!**")
        return
    
    user_data = stats["user_data"]
    collection = stats["collection"]
    rarity_count = stats["rarity_count"]
    total_value = stats["total_value"]
    
    # Extract data with defaults
    coins = user_data.get('coins', 0) or 0
    wins = user_data.get('total_wins', 0) or user_data.get('total_smash', 0) or 0
    losses = user_data.get('total_losses', 0) or user_data.get('total_pass', 0) or 0
    daily_streak = user_data.get('daily_streak', 0) or 0
    
    # Calculate stats
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    net_worth = coins + total_value
    
    # Get rank
    rank = get_user_rank(target.id)
    
    # Title and display name
    title = get_title(wins, len(collection))
    display_name = user_data.get("display_name") or target.first_name or "Unknown"
    username_str = f"@{target.username}" if target.username else "No Username"
    
    # Professional profile layout
    text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
        **PLAYER PROFILE**
━━━━━━━━━━━━━━━━━━━━━━━━

{title}
**{display_name}**
{username_str}

**Global Rank:** {get_rank_emoji(rank) if rank else 'Unranked'}

━━━━━━━━━━━━━━━━━━━━━━━━
        **📊 STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

**Battle Stats**
• Total Battles: **{total_games:,}**
• Victories: **{wins:,}**
• Defeats: **{losses:,}**
• Win Rate: **{win_rate:.1f}%**
• Daily Streak: **{daily_streak}** 🔥

**Economy**
• Balance: **{coins:,}** 💰
• Net Worth: **{net_worth:,}** 💎

━━━━━━━━━━━━━━━━━━━━━━━━
        **🎴 COLLECTION**
━━━━━━━━━━━━━━━━━━━━━━━━

**Total:** {len(collection)} waifus

🟡 **Legendary:** {rarity_count['legendary']}
🟣 **Epic:** {rarity_count['epic']}
🔵 **Rare:** {rarity_count['rare']}
⚪ **Common:** {rarity_count['common']}

**Value:** {total_value:,} 💎

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Detailed Stats", callback_data=f"pstats_{target.id}"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="lb_main")
        ],
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


async def rename_command(client: Client, message: Message):
    """Set display name"""
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/rename <new name>`\n\n"
            "Name must be 2-30 characters long."
        )
        return
    
    new_name = " ".join(message.command[1:])
    
    # Validate name
    if len(new_name) < 2:
        await message.reply_text("❌ **Name too short!** Minimum 2 characters.")
        return
    
    if len(new_name) > 30:
        await message.reply_text("❌ **Name too long!** Maximum 30 characters.")
        return
    
    # Check for special characters
    if not all(c.isalnum() or c.isspace() or c in "._-" for c in new_name):
        await message.reply_text("❌ **Invalid characters!** Use only letters, numbers, spaces, . _ -")
        return
    
    try:
        db.users.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"display_name": new_name}},
            upsert=True
        )
        await message.reply_text(
            f"✅ **Display Name Updated!**\n\n"
            f"New name: **{new_name}**"
        )
    except Exception as e:
        await message.reply_text(f"❌ **Database error:** {e}")


# ═══════════════════════════════════════════════════════════════════
#  LEADERBOARD COMMANDS
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
    status_msg = await message.reply_text("🔄 Loading top collectors...")
    
    top_users = get_top_collectors(10)
    
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
            count = user_data.get("_collection_count", 0)
            
            if i == 1:
                text += f"{medal} **{name}** — {count} waifus 💘🔥\n"
            elif i == 2:
                text += f"{medal} **{name}** — {count} waifus 💖✨\n"
            elif i == 3:
                text += f"{medal} **{name}** — {count} waifus 💕🌟\n"
            else:
                text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Full Leaderboard", callback_data="lb_main")]
    ])
    
    await status_msg.edit_text(text, reply_markup=buttons)


async def topwins_command(client: Client, message: Message):
    """Show top winners directly"""
    top_users = get_top_winners(10)
    
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
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Full Leaderboard", callback_data="lb_main")]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


async def toprich_command(client: Client, message: Message):
    """Show richest players directly"""
    top_users = get_top_rich(10)
    
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
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Full Leaderboard", callback_data="lb_main")]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def profile_stats_callback(client: Client, callback: CallbackQuery):
    """Detailed stats callback"""
    match = callback.matches[0] if callback.matches else None
    if not match:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    user_id = int(match.group(1))
    debug(f"Stats callback for {user_id}")
    
    stats = get_user_stats(user_id)
    if not stats:
        await callback.answer("❌ Error loading stats!", show_alert=True)
        return
    
    user_data = stats["user_data"]
    collection = stats["collection"]
    
    # Extended stats
    coins = user_data.get('coins', 0) or 0
    wins = user_data.get('total_wins', 0) or user_data.get('total_smash', 0) or 0
    losses = user_data.get('total_losses', 0) or user_data.get('total_pass', 0) or 0
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    daily_streak = user_data.get('daily_streak', 0) or 0
    total_earned = user_data.get('total_earned', coins) or coins
    total_spent = user_data.get('total_spent', 0) or 0
    net_profit = total_earned - total_spent
    
    # Best waifu (highest rarity)
    best_waifu = "None"
    if collection:
        rarity_order = {"legendary": 4, "epic": 3, "rare": 2, "common": 1}
        sorted_collection = sorted(
            collection,
            key=lambda x: rarity_order.get(str(x.get("waifu_rarity") or x.get("rarity", "common")).lower(), 0),
            reverse=True
        )
        if sorted_collection:
            best = sorted_collection[0]
            best_name = best.get("waifu_name") or best.get("name", "Unknown")
            best_rarity = str(best.get("waifu_rarity") or best.get("rarity", "common")).title()
            best_waifu = f"{best_name} ({best_rarity})"
    
    text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
    **DETAILED STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

**💰 Economy Analysis**
• Current Balance: **{coins:,}**
• Total Earned: **{total_earned:,}**
• Total Spent: **{total_spent:,}**
• Net Profit: **{'+' if net_profit >= 0 else ''}{net_profit:,}**

**⚔️ Battle Performance**
• Total Battles: **{total:,}**
• Victories: **{wins:,}**
• Defeats: **{losses:,}**
• Win Rate: **{win_rate:.2f}%**
• Win/Loss Ratio: **{wins/losses if losses > 0 else wins:.2f}**

**📊 Activity Metrics**
• Daily Streak: **{daily_streak}** days
• Avg Wins/Day: **{wins/max(daily_streak, 1):.1f}**
• Best Waifu: **{best_waifu}**

**🎴 Collection Analysis**
• Total Waifus: **{len(collection)}**
• Collection Value: **{calculate_value(collection):,}**
• Avg Waifu Value: **{calculate_value(collection)//max(len(collection), 1):,}**

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Back to Profile", callback_data=f"profile_{user_id}"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="lb_main")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except:
        await callback.message.reply_text(text, reply_markup=buttons)
    await callback.answer()


async def profile_back_callback(client: Client, callback: CallbackQuery):
    """Back to main profile"""
    match = callback.matches[0] if callback.matches else None
    if not match:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    user_id = int(match.group(1))
    
    try:
        target = await client.get_users(user_id)
    except:
        await callback.answer("❌ User not found!", show_alert=True)
        return
    
    # Get stats
    stats = get_user_stats(target.id)
    if not stats:
        await callback.answer("❌ Database error!", show_alert=True)
        return
    
    user_data = stats["user_data"]
    collection = stats["collection"]
    rarity_count = stats["rarity_count"]
    total_value = stats["total_value"]
    
    coins = user_data.get('coins', 0) or 0
    wins = user_data.get('total_wins', 0) or user_data.get('total_smash', 0) or 0
    losses = user_data.get('total_losses', 0) or user_data.get('total_pass', 0) or 0
    daily_streak = user_data.get('daily_streak', 0) or 0
    
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    net_worth = coins + total_value
    rank = get_user_rank(target.id)
    
    title = get_title(wins, len(collection))
    display_name = user_data.get("display_name") or target.first_name or "Unknown"
    username_str = f"@{target.username}" if target.username else "No Username"
    
    text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
        **PLAYER PROFILE**
━━━━━━━━━━━━━━━━━━━━━━━━

{title}
**{display_name}**
{username_str}

**Global Rank:** {get_rank_emoji(rank) if rank else 'Unranked'}

━━━━━━━━━━━━━━━━━━━━━━━━
        **📊 STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

**Battle Stats**
• Total Battles: **{total_games:,}**
• Victories: **{wins:,}**
• Defeats: **{losses:,}**
• Win Rate: **{win_rate:.1f}%**
• Daily Streak: **{daily_streak}** 🔥

**Economy**
• Balance: **{coins:,}** 💰
• Net Worth: **{net_worth:,}** 💎

━━━━━━━━━━━━━━━━━━━━━━━━
        **🎴 COLLECTION**
━━━━━━━━━━━━━━━━━━━━━━━━

**Total:** {len(collection)} waifus

🟡 **Legendary:** {rarity_count['legendary']}
🟣 **Epic:** {rarity_count['epic']}
🔵 **Rare:** {rarity_count['rare']}
⚪ **Common:** {rarity_count['common']}

**Value:** {total_value:,} 💎

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Detailed Stats", callback_data=f"pstats_{target.id}"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="lb_main")
        ],
        [
            InlineKeyboardButton("🎮 Play", callback_data="play_smash")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=buttons)
    except:
        pass
    await callback.answer()


async def lb_collectors_callback(client: Client, callback: CallbackQuery):
    """Show top collectors"""
    await callback.answer("Loading collectors...")
    
    top_users = get_top_collectors(10)
    
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
            count = user_data.get("_collection_count", 0)
            
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
    
    top_users = get_top_winners(10)
    
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
    
    top_users = get_top_rich(10)
    
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
    
    stats = get_global_stats()
    
    text = f"""
📊 **GLOBAL STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━

👥 **Total Users:** {stats['total_users']:,}
📦 **Waifus Collected:** {stats['total_waifus']:,}
💥 **Total Smashes:** {stats['total_smashes']:,}
👋 **Total Passes:** {stats['total_passes']:,}
💰 **Total Coins:** {stats['total_coins']:,}

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


async def noop_callback(client: Client, callback: CallbackQuery):
    """No operation callback for static buttons"""
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
#  SETUP FUNCTION
# ═══════════════════════════════════════════════════════════════════

def setup(app: Client):
    """Register all profile and leaderboard handlers"""
    
    # Profile commands
    app.add_handler(MessageHandler(
        profile_command,
        filters.command(["profile", "p"], config.COMMAND_PREFIX)
    ))
    
    app.add_handler(MessageHandler(
        rename_command,
        filters.command(["rename", "setname"], config.COMMAND_PREFIX)
    ))
    
    # Leaderboard commands
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
    
    # Profile callbacks
    app.add_handler(CallbackQueryHandler(
        profile_stats_callback,
        filters.regex(r"^pstats_(\d+)$")
    ))
    
    app.add_handler(CallbackQueryHandler(
        profile_back_callback,
        filters.regex(r"^profile_(\d+)$")
    ))
    
    # Leaderboard callbacks
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
    
    app.add_handler(CallbackQueryHandler(
        noop_callback,
        filters.regex("^noop$")
    ))
    
    logger.info("✅ Profile & Leaderboard module loaded successfully!")
