from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from helpers.utils import get_rarity_emoji, calculate_collection_value
from config import COMMAND_PREFIX
import math

__MODULE__ = "Profile"
__HELP__ = """
👤 **Profile Commands**

`.profile` - View your profile
`.profile @user` - View someone's profile
`.collection` - View your waifu collection
`.collection @user` - View someone's collection
`.waifuinfo <id>` - View waifu details
`.stats` - View your statistics
`.top` - View global leaderboard
`.topcoins` - Coins leaderboard
`.rename <name>` - Set display name
"""


@Client.on_message(filters.command(["profile", "p"], prefixes=COMMAND_PREFIX))
async def profile_cmd(client: Client, message: Message):
    """View user profile"""
    # Determine target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        target = message.from_user
    
    user_data = await db.get_user(target.id)
    collection = user_data.get("collection", [])
    
    # Calculate stats
    total_waifus = len(collection)
    total_value = calculate_collection_value(collection)
    
    # Count by rarity
    rarity_count = {}
    for waifu in collection:
        rarity = waifu.get("rarity", "Common")
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    # Get rank
    all_users = await db.users.find({}).to_list(length=None)
    sorted_users = sorted(
        all_users,
        key=lambda x: len(x.get("collection", [])),
        reverse=True
    )
    rank = next(
        (i + 1 for i, u in enumerate(sorted_users) if u["user_id"] == target.id),
        "N/A"
    )
    
    # Build profile text
    display_name = user_data.get("display_name", target.first_name)
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    text = f"""
╭─────────────────────╮
│     👤 **PROFILE**
╰─────────────────────╯

**Name:** {display_name}
**Username:** @{target.username or 'None'}
**ID:** `{target.id}`

╭─────────────────────╮
│     📊 **STATS**
╰─────────────────────╯

💰 **Coins:** {coins:,}
🏆 **Rank:** #{rank}
📦 **Waifus:** {total_waifus}
💎 **Value:** {total_value:,}

╭─────────────────────╮
│     🎮 **GAME STATS**
╰─────────────────────╯

✅ **Wins:** {wins}
❌ **Losses:** {losses}
📈 **Win Rate:** {win_rate:.1f}%

╭─────────────────────╮
│     📋 **COLLECTION**
╰─────────────────────╯
"""
    
    # Add rarity breakdown
    rarity_order = ["Legendary", "Epic", "Rare", "Uncommon", "Common"]
    for rarity in rarity_order:
        count = rarity_count.get(rarity, 0)
        emoji = get_rarity_emoji(rarity)
        text += f"\n{emoji} **{rarity}:** {count}"
    
    buttons = [
        [
            InlineKeyboardButton("📦 Collection", callback_data=f"col_{target.id}_1"),
            InlineKeyboardButton("📊 Stats", callback_data=f"stats_{target.id}")
        ]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command(["collection", "col", "waifus"], prefixes=COMMAND_PREFIX))
async def collection_cmd(client: Client, message: Message):
    """View waifu collection"""
    # Determine target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        target = message.from_user
    
    user_data = await db.get_user(target.id)
    collection = user_data.get("collection", [])
    
    if not collection:
        return await message.reply_text(f"📭'Your' if target.id == message.from_user.id else target.first_name + \"'s\" collection is empty!")
    
    await show_collection_page(message, target.id, 1)


async def show_collection_page(message_or_callback, user_id: int, page: int):
    """Show paginated collection"""
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    # Pagination
    per_page = 10
    total_pages = math.ceil(len(collection) / per_page)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_waifus = collection[start_idx:end_idx]
    
    text = f"📦 **Waifu Collection** (Page {page}/{total_pages})\n\n"
    
    for waifu in page_waifus:
        emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
        text += f"{emoji} **{waifu['name']}** [ID: {waifu['id']}]\n"
        text += f"   └ {waifu.get('anime', 'Unknown')}\n"
    
    text += f"\n📊 Total: {len(collection)} waifus"
    
    # Navigation buttons
    buttons = []
    nav_row = []
    
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_{user_id}_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_{user_id}_{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Rarity filter buttons
    buttons.append([
        InlineKeyboardButton("🌟 Legendary", callback_data=f"colfilter_{user_id}_Legendary"),
        InlineKeyboardButton("💜 Epic", callback_data=f"colfilter_{user_id}_Epic")
    ])
    buttons.append([
        InlineKeyboardButton("💙 Rare", callback_data=f"colfilter_{user_id}_Rare"),
        InlineKeyboardButton("💚 All", callback_data=f"col_{user_id}_1")
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message_or_callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^col_(\d+)_(\d+)$"))
async def collection_page_callback(client: Client, callback: CallbackQuery):
    """Handle collection pagination"""
    user_id = int(callback.matches[0].group(1))
    page = int(callback.matches[0].group(2))
    
    await show_collection_page(callback, user_id, page)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^colfilter_(\d+)_(\w+)$"))
async def collection_filter_callback(client: Client, callback: CallbackQuery):
    """Filter collection by rarity"""
    user_id = int(callback.matches[0].group(1))
    rarity = callback.matches[0].group(2)
    
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    filtered = [w for w in collection if w.get("rarity") == rarity]
    
    if not filtered:
        return await callback.answer(f"No {rarity} waifus found!", show_alert=True)
    
    text = f"📦 **{rarity} Waifus** ({len(filtered)})\n\n"
    
    emoji = get_rarity_emoji(rarity)
    for waifu in filtered[:15]:  # Show max 15
        text += f"{emoji} **{waifu['name']}** [ID: {waifu['id']}]\n"
    
    if len(filtered) > 15:
        text += f"\n... and {len(filtered) - 15} more"
    
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=f"col_{user_id}_1")]]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer()


@Client.on_message(filters.command(["waifuinfo", "wi", "info"], prefixes=COMMAND_PREFIX))
async def waifu_info_cmd(client: Client, message: Message):
    """View detailed waifu info"""
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.waifuinfo <waifu_id>`")
    
    try:
        waifu_id = int(message.command[1])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")
    
    user_data = await db.get_user(message.from_user.id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await message.reply_text("❌ Waifu not found in your collection!")
    
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    value = waifu.get("value", 100)
    
    text = f"""
{emoji} **{waifu['name']}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
⭐ **Rarity:** {waifu.get('rarity', 'Common')}
💰 **Value:** {value:,} coins
🆔 **ID:** {waifu['id']}
📅 **Obtained:** {waifu.get('obtained_at', 'Unknown')}
"""
    
    # If waifu has image
    if waifu.get("image"):
        buttons = [
            [
                InlineKeyboardButton("🎁 Gift", callback_data=f"giftsel_{waifu_id}"),
                InlineKeyboardButton("💰 Sell", callback_data=f"sell_{waifu_id}")
            ]
        ]
        await message.reply_photo(
            photo=waifu["image"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        buttons = [
            [
                InlineKeyboardButton("🎁 Gift", callback_data=f"giftsel_{waifu_id}"),
                InlineKeyboardButton("💰 Sell", callback_data=f"sell_{waifu_id}")
            ]
        ]
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command(["stats", "mystats"], prefixes=COMMAND_PREFIX))
async def stats_cmd(client: Client, message: Message):
    """View detailed statistics"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    collection = user_data.get("collection", [])
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    daily_streak = user_data.get("daily_streak", 0)
    total_earned = user_data.get("total_earned", 0)
    total_spent = user_data.get("total_spent", 0)
    
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    collection_value = calculate_collection_value(collection)
    
    text = f"""
📊 **Your Statistics**

╭─────────────────────╮
│     💰 **ECONOMY**
╰─────────────────────╯

💵 **Current Coins:** {coins:,}
📈 **Total Earned:** {total_earned:,}
📉 **Total Spent:** {total_spent:,}
💎 **Collection Value:** {collection_value:,}
🏦 **Net Worth:** {coins + collection_value:,}

╭─────────────────────╮
│     🎮 **GAMES**
╰─────────────────────╯

🎯 **Total Games:** {total_games}
✅ **Wins:** {wins}
❌ **Losses:** {losses}
📈 **Win Rate:** {win_rate:.1f}%

╭─────────────────────╮
│     📦 **COLLECTION**
╰─────────────────────╯

📦 **Total Waifus:** {len(collection)}
🔥 **Daily Streak:** {daily_streak} days
"""
    
    await message.reply_text(text)


@Client.on_message(filters.command(["top", "leaderboard", "lb"], prefixes=COMMAND_PREFIX))
async def leaderboard_cmd(client: Client, message: Message):
    """View global leaderboard"""
    all_users = await db.users.find({}).to_list(length=100)
    
    # Sort by collection size
    sorted_users = sorted(
        all_users,
        key=lambda x: len(x.get("collection", [])),
        reverse=True
    )[:10]
    
    text = "🏆 **Global Leaderboard**\n\n"
    text += "**Top Collectors:**\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        collection_size = len(user.get("collection", []))
        
        try:
            tg_user = await db.client.get_users(user["user_id"])
            name = tg_user.first_name
        except:
            name = user.get("display_name", "Unknown")
        
        text += f"{medal} {name} - **{collection_size}** waifus\n"
    
    buttons = [
        [
            InlineKeyboardButton("💰 Coins LB", callback_data="lb_coins"),
            InlineKeyboardButton("🎮 Wins LB", callback_data="lb_wins")
        ]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^lb_(coins|wins)$"))
async def leaderboard_type_callback(client: Client, callback: CallbackQuery):
    """Show different leaderboard types"""
    lb_type = callback.matches[0].group(1)
    
    all_users = await db.users.find({}).to_list(length=100)
    
    if lb_type == "coins":
        sorted_users = sorted(all_users, key=lambda x: x.get("coins", 0), reverse=True)[:10]
        title = "💰 **Coins Leaderboard**"
        field = "coins"
        suffix = "coins"
    else:
        sorted_users = sorted(all_users, key=lambda x: x.get("wins", 0), reverse=True)[:10]
        title = "🎮 **Wins Leaderboard**"
        field = "wins"
        suffix = "wins"
    
    text = f"{title}\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        value = user.get(field, 0)
        name = user.get("display_name", f"User_{user['user_id']}")
        text += f"{medal} {name} - **{value:,}** {suffix}\n"
    
    buttons = [
        [
            InlineKeyboardButton("📦 Collection LB", callback_data="lb_collection"),
            InlineKeyboardButton("🔙 Back", callback_data="lb_collection")
        ]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer()


@Client.on_message(filters.command(["rename", "setname"], prefixes=COMMAND_PREFIX))
async def rename_cmd(client: Client, message: Message):
    """Set display name"""
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.rename <new_name>`")
    
    new_name = " ".join(message.command[1:])
    
    if len(new_name) > 30:
        return await message.reply_text("❌ Name too long! Max 30 characters.")
    
    if len(new_name) < 2:
        return await message.reply_text("❌ Name too short! Min 2 characters.")
    
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"display_name": new_name}}
    )
    
    await message.reply_text(f"✅ Display name changed to: **{new_name}**")