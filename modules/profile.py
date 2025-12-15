# modules/profile.py - Professional Profile System (FIXED COLLECTION COUNT)

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
import math

__MODULE__ = "𝐏𝐫𝐨𝐟𝐢𝐥𝐞"
__HELP__ = """
👤 **Profile Commands**
/profile - View your profile
/profile @user - View someone's profile
/rename <name> - Set display name
"""

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"👤 [PROFILE] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity - Updated order"""
    return {
        "common": "⚪",
        "epic": "🟣",
        "legendary": "🟡",
        "rare": "🔵"
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
        "epic": 25,
        "legendary": 50,
        "rare": 100
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


def get_user_stats(user_id: int) -> dict:
    """Get comprehensive user statistics - FIXED COLLECTION FETCHING"""
    try:
        user_data = db.get_user(user_id)
        if not user_data:
            user_data = {}
        
        # FIXED: Get FULL collection using direct database query
        try:
            # Direct MongoDB query to get ALL waifus for user
            user_doc = db.users.find_one({"user_id": user_id})
            if user_doc and "collection" in user_doc:
                collection = user_doc["collection"]
            else:
                collection = []
            
            # If collection is still empty or limited, try alternative method
            if len(collection) < 10:  # Suspicious if less than 10
                # Try using get_full_collection if available
                if hasattr(db, 'get_full_collection'):
                    collection = db.get_full_collection(user_id) or []
                # Or try get_user_collection without limit
                elif hasattr(db, 'get_user_collection'):
                    collection = db.get_user_collection(user_id) or []
            
            debug(f"Fetched {len(collection)} waifus for user {user_id}")
            
        except Exception as e:
            debug(f"Error fetching collection: {e}")
            collection = []
        
        # Count by rarity - Updated order
        rarity_count = {"common": 0, "epic": 0, "legendary": 0, "rare": 0}
        for w in collection:
            r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
            if r in rarity_count:
                rarity_count[r] += 1
        
        debug(f"Rarity counts: {rarity_count}")
        
        return {
            "user_data": user_data,
            "collection": collection,
            "rarity_count": rarity_count,
            "total_value": calculate_value(collection)
        }
    except Exception as e:
        debug(f"Error getting stats: {e}")
        return None


def get_all_users_with_collections():
    """Get all users with their FULL collection data"""
    try:
        all_users = list(db.users.find({}))
        users_with_collections = []
        
        for user in all_users:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            # Get FULL collection directly from user document
            collection = user.get("collection", [])
            
            # If collection seems limited, try alternative methods
            if len(collection) < 10 and collection:
                if hasattr(db, 'get_full_collection'):
                    collection = db.get_full_collection(user_id) or collection
                elif hasattr(db, 'get_user_collection'):
                    collection = db.get_user_collection(user_id) or collection
            
            # Add collection data to user
            user_with_collection = user.copy()
            user_with_collection["_collection"] = collection
            user_with_collection["_collection_count"] = len(collection)
            user_with_collection["_collection_value"] = calculate_value(collection)
            
            users_with_collections.append(user_with_collection)
        
        return users_with_collections
    except Exception as e:
        debug(f"Error getting users with collections: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
#  /profile Command - Professional Design
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["profile", "p"], config.COMMAND_PREFIX))
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
    
    # Debug collection count
    debug(f"Collection count for {target.id}: {len(collection)}")
    debug(f"First few waifus: {[w.get('waifu_name') or w.get('name') for w in collection[:5]]}")
    
    # Extract data with defaults
    coins = user_data.get('coins', 0)
    wins = user_data.get('total_wins', 0)
    losses = user_data.get('total_losses', 0)
    total_smash = user_data.get('total_smash', 0)
    daily_streak = user_data.get('daily_streak', 0)
    
    # Calculate stats
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    net_worth = coins + total_value
    
    # Get rank - FIXED to use proper collection data
    try:
        all_users = get_all_users_with_collections()
        
        # Sort by net worth (coins + collection value)
        sorted_users = sorted(
            all_users, 
            key=lambda x: x.get('coins', 0) + x.get('_collection_value', 0), 
            reverse=True
        )
        rank = next((i+1 for i, u in enumerate(sorted_users) if u.get("user_id") == target.id), 0)
    except:
        rank = 0
    
    # Title and display name
    title = get_title(wins, len(collection))
    display_name = user_data.get("display_name", target.first_name)
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
        **🎴 WAIFUS**
━━━━━━━━━━━━━━━━━━━━━━━━

**Total:** {len(collection)} waifus

🔵 **Rare:** {rarity_count['rare']}
🟡 **Legendary:** {rarity_count['legendary']}  
🟣 **Epic:** {rarity_count['epic']}
⚪ **Common:** {rarity_count['common']}

**Value:** {total_value:,} 💎

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 DETAILED STATS", callback_data=f"pstats_{target.id}")
        ],
        [
            InlineKeyboardButton("📈 LEADERBOARD", callback_data="lb_main")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /rename Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["rename", "setname"], config.COMMAND_PREFIX))
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
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pstats_(\d+)$"))
async def profile_stats_callback(client: Client, callback: CallbackQuery):
    """Detailed stats callback - Professional layout"""
    user_id = int(callback.matches[0].group(1))
    
    debug(f"Stats callback for {user_id}")
    
    stats = get_user_stats(user_id)
    if not stats:
        await callback.answer("❌ Error loading stats!", show_alert=True)
        return
    
    user_data = stats["user_data"]
    collection = stats["collection"]
    
    # Extended stats
    coins = user_data.get('coins', 0)
    wins = user_data.get('total_wins', 0)
    losses = user_data.get('total_losses', 0)
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    daily_streak = user_data.get('daily_streak', 0)
    total_earned = user_data.get('total_earned', coins)
    total_spent = user_data.get('total_spent', 0)
    net_profit = total_earned - total_spent
    
    # Best waifu (highest rarity)
    best_waifu = "None"
    if collection:
        rarity_order = {"rare": 4, "legendary": 3, "epic": 2, "common": 1}
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
            InlineKeyboardButton("👤 MAIN PROFILE", callback_data=f"profile_{user_id}")
        ],
        [
            InlineKeyboardButton("📊STATS", callback_data="View_stats")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^profile_(\d+)$"))
async def profile_back_callback(client: Client, callback: CallbackQuery):
    """Back to main profile"""
    user_id = int(callback.matches[0].group(1))
    
    # Just trigger the profile command logic
    try:
        target = await client.get_users(user_id)
    except:
        await callback.answer("❌ User not found!", show_alert=True)
        return
    
    # Reuse profile command logic
    callback.message.from_user = callback.from_user
    callback.message.text = f"/profile {user_id}"
    await profile_command(client, callback.message)
    await callback.answer()


@Client.on_callback_query(filters.regex("^noop$"))
async def noop_callback(client: Client, callback: CallbackQuery):
    """No operation callback for static buttons"""
    await callback.answer()
