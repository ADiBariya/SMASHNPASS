# modules/profile.py - Sexy Profile System

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

__MODULE__ = "Profile"
__HELP__ = """
👤 **Profile Commands**
/profile - View your profile
/profile @user - View someone's profile
/collection - View waifu collection
/top - Global leaderboard
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


def calculate_value(collection: list) -> int:
    """Calculate total collection value"""
    values = {
        "common": 10,
        "uncommon": 25,
        "rare": 50,
        "epic": 100,
        "legendary": 500
    }
    total = 0
    for w in collection:
        r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
        total += values.get(r, 10)
    return total


def get_title(collection_count: int) -> str:
    """Get user title based on collection"""
    if collection_count >= 100:
        return "🌟 Waifu Master"
    elif collection_count >= 50:
        return "💫 Waifu Collector"
    elif collection_count >= 25:
        return "✨ Waifu Hunter"
    elif collection_count >= 10:
        return "⭐ Waifu Fan"
    else:
        return "🌱 Beginner"


# ═══════════════════════════════════════════════════════════════════
#  /profile Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["profile", "p"], config.COMMAND_PREFIX))
async def profile_command(client: Client, message: Message):
    """View user profile"""
    debug(f"Profile command from {message.from_user.id}")
    
    # Get target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            await message.reply_text("❌ User not found!")
            return
    else:
        target = message.from_user
    
    debug(f"Viewing profile for {target.id}")
    
    # Get user data
    try:
        user_data = db.get_or_create_user(target.id, target.username, target.first_name)
        collection = db.get_user_collection(target.id)
    except Exception as e:
        debug(f"DB error: {e}")
        await message.reply_text(f"❌ Database error: {e}")
        return
    
    collection = collection or []
    collection_count = len(collection)
    
    # Stats
    coins = user_data.get('coins', 0)
    wins = user_data.get('total_wins', user_data.get('wins', 0))
    losses = user_data.get('total_losses', user_data.get('losses', 0))
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    # Collection value
    collection_value = calculate_value(collection)
    
    # Count by rarity
    rarity_count = {"legendary": 0, "epic": 0, "rare": 0, "uncommon": 0, "common": 0}
    for w in collection:
        r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
        if r in rarity_count:
            rarity_count[r] += 1
    
    # Get rank (simplified)
    rank = "N/A"
    try:
        all_users = list(db.users.find({}))
        sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)
        for i, u in enumerate(sorted_users):
            if u.get("user_id") == target.id:
                rank = i + 1
                break
    except:
        pass
    
    # Title
    title = get_title(collection_count)
    display_name = user_data.get("display_name", target.first_name)
    
    text = f"""
╔═══════════════════════════════╗
          👤 **PROFILE**
╚═══════════════════════════════╝

{title}
**{display_name}**
━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Basic Info**
┣ 🆔 ID: `{target.id}`
┣ 👤 @{target.username or 'None'}
┗ 🏆 Rank: {get_rank_emoji(rank) if isinstance(rank, int) else rank}

━━━━━━━━━━━━━━━━━━━━━━━━

💰 **Wealth**
┣ 💵 Coins: **{coins:,}**
┣ 💎 Value: **{collection_value:,}**
┗ 🏦 Net Worth: **{coins + collection_value:,}**

━━━━━━━━━━━━━━━━━━━━━━━━

📦 **Collection** ({collection_count})
┣ 🟡 Legendary: {rarity_count['legendary']}
┣ 🟣 Epic: {rarity_count['epic']}
┣ 🔵 Rare: {rarity_count['rare']}
┗ ⚪ Common: {rarity_count['common']}

━━━━━━━━━━━━━━━━━━━━━━━━

🎮 **Game Stats**
┣ ✅ Wins: {wins}
┣ ❌ Losses: {losses}
┗ 📈 Win Rate: **{win_rate:.1f}%**

╔═══════════════════════════════╗
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Collection", callback_data=f"pcol_{target.id}_1"),
            InlineKeyboardButton("📊 Stats", callback_data=f"pstats_{target.id}")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="lb_collection")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /collection Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["collection", "col", "waifus"], config.COMMAND_PREFIX))
async def collection_command(client: Client, message: Message):
    """View waifu collection"""
    debug(f"Collection command from {message.from_user.id}")
    
    # Get target
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            await message.reply_text("❌ User not found!")
            return
    else:
        target = message.from_user
    
    await show_collection(message, target.id, 1)


async def show_collection(msg_or_cb, user_id: int, page: int, edit: bool = False):
    """Show collection page"""
    debug(f"Showing collection for {user_id}, page {page}")
    
    try:
        collection = db.get_user_collection(user_id)
    except Exception as e:
        debug(f"DB error: {e}")
        return
    
    collection = collection or []
    
    if not collection:
        text = """
📦 **Collection Empty**

━━━━━━━━━━━━━━━━━━━━━━━━
😢 No waifus yet!

Play /smash to start collecting!
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")]
        ])
        
        if edit and hasattr(msg_or_cb, 'message'):
            await msg_or_cb.message.edit_text(text, reply_markup=buttons)
        else:
            await msg_or_cb.reply_text(text, reply_markup=buttons)
        return
    
    # Pagination
    per_page = 8
    total_pages = max(1, math.ceil(len(collection) / per_page))
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * per_page
    end = start + per_page
    page_items = collection[start:end]
    
    text = f"""
📦 **Waifu Collection**

━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total: **{len(collection)}** | Page {page}/{total_pages}
━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, waifu in enumerate(page_items, start + 1):
        name = waifu.get("waifu_name") or waifu.get("name", "Unknown")
        rarity = waifu.get("waifu_rarity") or waifu.get("rarity", "common")
        power = waifu.get("waifu_power") or waifu.get("power", 0)
        anime = waifu.get("waifu_anime") or waifu.get("anime", "?")
        wid = waifu.get("waifu_id") or waifu.get("id", 0)
        emoji = get_rarity_emoji(rarity)
        
        text += f"{emoji} **{name}**\n"
        text += f"   ┗ 📺 {anime[:20]} | ⚔️ {power}\n\n"
    
    # Navigation buttons
    buttons = []
    nav_row = []
    
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"pcol_{user_id}_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"pcol_{user_id}_{page+1}"))
    
    buttons.append(nav_row)
    
    # Filter buttons
    buttons.append([
        InlineKeyboardButton("🟡 Legend", callback_data=f"pfilter_{user_id}_legendary"),
        InlineKeyboardButton("🟣 Epic", callback_data=f"pfilter_{user_id}_epic"),
        InlineKeyboardButton("🔵 Rare", callback_data=f"pfilter_{user_id}_rare")
    ])
    
    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data=f"pback_{user_id}")
    ])
    
    if edit and hasattr(msg_or_cb, 'message'):
        await msg_or_cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await msg_or_cb.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ═══════════════════════════════════════════════════════════════════
#  /top Command (Leaderboard)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["top", "leaderboard", "lb"], config.COMMAND_PREFIX))
async def leaderboard_command(client: Client, message: Message):
    """Show global leaderboard"""
    debug(f"Leaderboard command from {message.from_user.id}")
    
    try:
        all_users = list(db.users.find({}))
    except Exception as e:
        debug(f"DB error: {e}")
        await message.reply_text(f"❌ Database error: {e}")
        return
    
    # Sort by collection size
    sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)[:10]
    
    text = """
🏆 **Global Leaderboard**

━━━━━━━━━━━━━━━━━━━━━━━━
📦 **Top Collectors**
━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, user in enumerate(sorted_users, 1):
        name = user.get("display_name") or user.get("first_name", f"User {user.get('user_id', '?')}")
        count = len(user.get("collection", []))
        medal = get_rank_emoji(i)
        
        text += f"{medal} **{name}** — {count} waifus\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Coins", callback_data="lb_coins"),
            InlineKeyboardButton("🎮 Wins", callback_data="lb_wins")
        ],
        [
            InlineKeyboardButton("📦 Collection", callback_data="lb_collection")
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
        await message.reply_text("❌ **Usage:** `/rename <new name>`")
        return
    
    new_name = " ".join(message.command[1:])
    
    if not (2 <= len(new_name) <= 30):
        await message.reply_text("❌ Name must be 2-30 characters!")
        return
    
    try:
        db.users.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"display_name": new_name}}
        )
        await message.reply_text(f"✅ Display name set to: **{new_name}**")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pcol_(\d+)_(\d+)$"))
async def collection_page_callback(client: Client, callback: CallbackQuery):
    """Collection page navigation"""
    user_id = int(callback.matches[0].group(1))
    page = int(callback.matches[0].group(2))
    
    debug(f"Collection page callback: user={user_id}, page={page}")
    
    await show_collection(callback, user_id, page, edit=True)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^pfilter_(\d+)_(\w+)$"))
async def collection_filter_callback(client: Client, callback: CallbackQuery):
    """Filter collection by rarity"""
    user_id = int(callback.matches[0].group(1))
    rarity = callback.matches[0].group(2)
    
    debug(f"Filter callback: user={user_id}, rarity={rarity}")
    
    try:
        collection = db.get_user_collection(user_id)
    except:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    collection = collection or []
    
    # Filter
    filtered = []
    for w in collection:
        r = str(w.get("waifu_rarity") or w.get("rarity", "common")).lower()
        if r == rarity.lower():
            filtered.append(w)
    
    if not filtered:
        await callback.answer(f"No {rarity} waifus!", show_alert=True)
        return
    
    emoji = get_rarity_emoji(rarity)
    
    text = f"""
📦 **{rarity.title()} Waifus** ({len(filtered)})

━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for w in filtered[:12]:
        name = w.get("waifu_name") or w.get("name", "Unknown")
        power = w.get("waifu_power") or w.get("power", 0)
        text += f"{emoji} **{name}** (⚔️ {power})\n"
    
    if len(filtered) > 12:
        text += f"\n... and {len(filtered) - 12} more"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"pcol_{user_id}_1")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^pstats_(\d+)$"))
async def profile_stats_callback(client: Client, callback: CallbackQuery):
    """Detailed stats callback"""
    user_id = int(callback.matches[0].group(1))
    
    debug(f"Stats callback for {user_id}")
    
    try:
        user_data = db.get_user(user_id)
        collection = db.get_user_collection(user_id)
    except:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    collection = collection or []
    
    coins = user_data.get('coins', 0)
    wins = user_data.get('total_wins', user_data.get('wins', 0))
    losses = user_data.get('total_losses', user_data.get('losses', 0))
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    daily_streak = user_data.get('daily_streak', 0)
    total_earned = user_data.get('total_earned', 0)
    total_spent = user_data.get('total_spent', 0)
    
    text = f"""
📊 **Detailed Statistics**

━━━━━━━━━━━━━━━━━━━━━━━━

💰 **Economy**
┣ 💵 Balance: **{coins:,}**
┣ 📈 Total Earned: {total_earned:,}
┣ 📉 Total Spent: {total_spent:,}
┗ 💎 Collection Value: {calculate_value(collection):,}

━━━━━━━━━━━━━━━━━━━━━━━━

🎮 **Gaming**
┣ 🎯 Total Games: {total}
┣ ✅ Wins: {wins}
┣ ❌ Losses: {losses}
┗ 📈 Win Rate: **{win_rate:.1f}%**

━━━━━━━━━━━━━━━━━━━━━━━━

📅 **Activity**
┣ 🔥 Daily Streak: {daily_streak} days
┗ 📦 Waifus: {len(collection)}

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"pback_{user_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^pback_(\d+)$"))
async def profile_back_callback(client: Client, callback: CallbackQuery):
    """Back to profile"""
    user_id = int(callback.matches[0].group(1))
    
    debug(f"Back to profile for {user_id}")
    
    # Simplified - just show collection page 1
    await show_collection(callback, user_id, 1, edit=True)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^lb_(coins|wins|collection)$"))
async def leaderboard_type_callback(client: Client, callback: CallbackQuery):
    """Leaderboard type switch"""
    lb_type = callback.matches[0].group(1)
    
    debug(f"Leaderboard type: {lb_type}")
    
    try:
        all_users = list(db.users.find({}))
    except:
        await callback.answer("❌ Error!", show_alert=True)
        return
    
    if lb_type == "coins":
        sorted_users = sorted(all_users, key=lambda x: x.get("coins", 0), reverse=True)[:10]
        title = "💰 **Coins Leaderboard**"
        field = "coins"
        suffix = "coins"
    elif lb_type == "wins":
        sorted_users = sorted(all_users, key=lambda x: x.get("total_wins", x.get("wins", 0)), reverse=True)[:10]
        title = "🎮 **Wins Leaderboard**"
        field = "wins"
        suffix = "wins"
    else:
        sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)[:10]
        title = "📦 **Collection Leaderboard**"
        field = None
        suffix = "waifus"
    
    text = f"""
🏆 {title}

━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, user in enumerate(sorted_users, 1):
        name = user.get("display_name") or user.get("first_name", f"User")
        
        if field == "coins":
            value = user.get("coins", 0)
        elif field == "wins":
            value = user.get("total_wins", user.get("wins", 0))
        else:
            value = len(user.get("collection", []))
        
        medal = get_rank_emoji(i)
        text += f"{medal} **{name}** — {value:,} {suffix}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Collection", callback_data="lb_collection"),
            InlineKeyboardButton("💰 Coins", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton("🎮 Wins", callback_data="lb_wins")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Client.on_callback_query(filters.regex("^noop$"))
async def noop_callback(client: Client, callback: CallbackQuery):
    """No operation callback for static buttons"""
    await callback.answer()
