from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
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


# ---------- SAFE MARKDOWN ESCAPE ----------
def md_escape(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text else ""
    return (
        text.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("`", "\\`")
    )


# ------------------ PROFILE COMMAND ------------------ #

@Client.on_message(filters.command(["profile", "p"], prefixes=COMMAND_PREFIX))
async def profile_cmd(client: Client, message: Message):

    # Get target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        target = message.from_user

    user_data = db.get_user(target.id)
    collection = user_data.get("collection", [])

    # Stats
    total_waifus = len(collection)
    total_value = calculate_collection_value(collection)

    # Count rarity
    rarity_count = {}
    for waifu in collection:
        rarity = waifu.get("rarity", "Common")
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1

    # GLOBAL RANK
    all_users = list(db.users.find({}))
    sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)
    rank = next((i + 1 for i, u in enumerate(sorted_users) if u["user_id"] == target.id), "N/A")

    display_name = md_escape(user_data.get("display_name", target.first_name))
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

    await message.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(buttons), 
        parse_mode=ParseMode.MARKDOWN
    )


# ------------------ COLLECTION ------------------ #

@Client.on_message(filters.command(["collection", "col", "waifus"], prefixes=COMMAND_PREFIX))
async def collection_cmd(client: Client, message: Message):

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        target = message.from_user

    user_data = db.get_user(target.id)
    collection = user_data.get("collection", [])

    if not collection:
        owner = "Your" if target.id == message.from_user.id else f"{target.first_name}'s"
        return await message.reply_text(f"📭 {owner} collection is empty!")

    await show_collection_page(message, target.id, 1)


async def show_collection_page(msg_or_cb, user_id: int, page: int):

    user_data = db.get_user(user_id)
    collection = user_data.get("collection", [])

    per_page = 10
    total_pages = max(1, math.ceil(len(collection) / per_page))
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_items = collection[start:end]

    text = f"📦 **Waifu Collection** (Page {page}/{total_pages})\n\n"

    for waifu in page_items:
        safe_name = md_escape(waifu.get("name", "Unknown"))
        safe_anime = md_escape(waifu.get("anime", "Unknown"))
        emoji = get_rarity_emoji(waifu.get("rarity", "Common"))

        text += f"{emoji} **{safe_name}** \\[ID: {waifu.get('id', 0)}\\]\n"
        text += f"   └ {safe_anime}\n"

    text += f"\n📊 Total: {len(collection)} waifus"

    buttons = []
    row = []

    if page > 1:
        row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_{user_id}_{page - 1}"))
    if page < total_pages:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_{user_id}_{page + 1}"))

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🌟 Legendary", callback_data=f"colfilter_{user_id}_Legendary"),
        InlineKeyboardButton("💜 Epic", callback_data=f"colfilter_{user_id}_Epic")
    ])
    buttons.append([
        InlineKeyboardButton("💙 Rare", callback_data=f"colfilter_{user_id}_Rare"),
        InlineKeyboardButton("💚 All", callback_data=f"col_{user_id}_1")
    ])

    markup = InlineKeyboardMarkup(buttons)

    if isinstance(msg_or_cb, Message):
        await msg_or_cb.reply_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await msg_or_cb.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


# ------------------ CALLBACKS ------------------ #

@Client.on_callback_query(filters.regex(r"^col_(\d+)_(\d+)$"))
async def cb_collection_page(client: Client, cb: CallbackQuery):
    user_id = int(cb.matches[0].group(1))
    page = int(cb.matches[0].group(2))
    await show_collection_page(cb, user_id, page)
    await cb.answer()


@Client.on_callback_query(filters.regex(r"^colfilter_(\d+)_(\w+)$"))
async def cb_collection_filter(client: Client, cb: CallbackQuery):

    user_id = int(cb.matches[0].group(1))
    rarity = cb.matches[0].group(2)

    user_data = db.get_user(user_id)
    collection = user_data.get("collection", [])
    filtered = [w for w in collection if w.get("rarity") == rarity]

    if not filtered:
        return await cb.answer(f"No {rarity} waifus found!", show_alert=True)

    emoji = get_rarity_emoji(rarity)

    text = f"📦 **{rarity} Waifus** ({len(filtered)})\n\n"
    for waifu in filtered[:15]:
        safe_name = md_escape(waifu.get("name", "Unknown"))
        text += f"{emoji} **{safe_name}** \\[ID: {waifu.get('id', 0)}\\]\n"

    if len(filtered) > 15:
        text += f"\n... and {len(filtered) - 15} more"

    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"col_{user_id}_1")]]),
        parse_mode=ParseMode.MARKDOWN
    )
    await cb.answer()


@Client.on_callback_query(filters.regex(r"^stats_(\d+)$"))
async def cb_stats(client: Client, cb: CallbackQuery):
    user_id = int(cb.matches[0].group(1))
    user_data = db.get_user(user_id)
    
    collection = user_data.get("collection", [])
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games else 0
    collection_value = calculate_collection_value(collection)
    
    text = f"""
📊 **User Statistics**

💰 **Coins:** {coins:,}
💎 **Collection Value:** {collection_value:,}
📦 **Waifus:** {len(collection)}

🎮 **Games:** {total_games}
✅ **Wins:** {wins}
❌ **Losses:** {losses}
📈 **Win Rate:** {win_rate:.1f}%
"""
    
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=f"col_{user_id}_1")]]
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)
    await cb.answer()


# ------------------ WAIFU INFO ------------------ #

@Client.on_message(filters.command(["waifuinfo", "wi", "info"], prefixes=COMMAND_PREFIX))
async def waifu_info_cmd(client: Client, message: Message):

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.waifuinfo <waifu_id>`")

    try:
        waifu_id = int(message.command[1])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")

    user_data = db.get_user(message.from_user.id)
    collection = user_data.get("collection", [])

    waifu = next((w for w in collection if w.get("id") == waifu_id), None)

    if not waifu:
        return await message.reply_text("❌ Waifu not found in your collection!")

    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    value = waifu.get("value", 100)

    safe_name = md_escape(waifu.get("name", "Unknown"))
    safe_anime = md_escape(waifu.get("anime", "Unknown"))

    text = f"""
{emoji} **{safe_name}**

📺 **Anime:** {safe_anime}
⭐ **Rarity:** {waifu.get('rarity', 'Common')}
💰 **Value:** {value:,} coins
🆔 **ID:** {waifu.get('id', 0)}
📅 **Obtained:** {waifu.get('obtained_at', 'Unknown')}
"""

    buttons = [
        [
            InlineKeyboardButton("🎁 Gift", callback_data=f"giftsel_{waifu_id}"),
            InlineKeyboardButton("💰 Sell", callback_data=f"sell_{waifu_id}")
        ]
    ]

    if waifu.get("image"):
        await message.reply_photo(
            waifu["image"], 
            caption=text, 
            reply_markup=InlineKeyboardMarkup(buttons), 
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(buttons), 
            parse_mode=ParseMode.MARKDOWN
        )


# ------------------ STATS ------------------ #

@Client.on_message(filters.command(["stats", "mystats"], prefixes=COMMAND_PREFIX))
async def stats_cmd(client: Client, message: Message):

    user_id = message.from_user.id
    user_data = db.get_user(user_id)

    collection = user_data.get("collection", [])
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    daily_streak = user_data.get("daily_streak", 0)
    total_earned = user_data.get("total_earned", 0)
    total_spent = user_data.get("total_spent", 0)

    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games else 0
    collection_value = calculate_collection_value(collection)

    text = f"""
📊 **Your Statistics**

💰 **Balance:** {coins:,}
💎 **Collection Value:** {collection_value:,}
🏦 **Net Worth:** {coins + collection_value:,}

🎮 **Games**
• Wins: {wins}
• Losses: {losses}
• Win Rate: {win_rate:.1f}%

📦 **Collection:** {len(collection)} waifus
🔥 **Daily Streak:** {daily_streak} days

📈 Earned: {total_earned:,}
📉 Spent: {total_spent:,}
"""

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ------------------ LEADERBOARD ------------------ #

@Client.on_message(filters.command(["top", "leaderboard", "lb"], prefixes=COMMAND_PREFIX))
async def leaderboard_cmd(client: Client, message: Message):

    all_users = list(db.users.find({}))

    sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)[:10]

    text = "🏆 **Global Leaderboard**\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = md_escape(user.get("display_name", f"User\\_{user['user_id']}"))
        count = len(user.get("collection", []))
        text += f"{medal} {name} — **{count}** waifus\n"

    buttons = [
        [
            InlineKeyboardButton("💰 Coins LB", callback_data="lb_coins"),
            InlineKeyboardButton("🎮 Wins LB", callback_data="lb_wins")
        ]
    ]

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)


# ------------------ CALLBACK (LB TYPES) ------------------ #

@Client.on_callback_query(filters.regex(r"^lb_(coins|wins|collection)$"))
async def leaderboard_type_callback(client: Client, cb: CallbackQuery):

    lb_type = cb.matches[0].group(1)
    all_users = list(db.users.find({}))

    if lb_type == "coins":
        sorted_users = sorted(all_users, key=lambda x: x.get("coins", 0), reverse=True)[:10]
        title = "💰 **Coins Leaderboard**"
        field = "coins"
        suffix = "coins"
    elif lb_type == "wins":
        sorted_users = sorted(all_users, key=lambda x: x.get("wins", 0), reverse=True)[:10]
        title = "🎮 **Wins Leaderboard**"
        field = "wins"
        suffix = "wins"
    else:  # collection
        sorted_users = sorted(all_users, key=lambda x: len(x.get("collection", [])), reverse=True)[:10]
        title = "🏆 **Collection Leaderboard**"
        field = None
        suffix = "waifus"

    text = f"{title}\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = md_escape(user.get("display_name", f"User\\_{user['user_id']}"))
        
        if field:
            value = user.get(field, 0)
        else:
            value = len(user.get("collection", []))
        
        text += f"{medal} {name} — **{value:,}** {suffix}\n"

    buttons = [
        [
            InlineKeyboardButton("📦 Collection", callback_data="lb_collection"),
            InlineKeyboardButton("💰 Coins", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton("🎮 Wins", callback_data="lb_wins")
        ]
    ]

    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)
    await cb.answer()


# ------------------ RENAME ------------------ #

@Client.on_message(filters.command(["rename", "setname"], prefixes=COMMAND_PREFIX))
async def rename_cmd(client: Client, message: Message):

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.rename <new_name>`")

    new_name = " ".join(message.command[1:])
    if not (2 <= len(new_name) <= 30):
        return await message.reply_text("❌ Name must be 2–30 characters.")

    db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"display_name": new_name}}
    )

    safe = md_escape(new_name)
    await message.reply_text(f"✅ Display name changed to: **{safe}**", parse_mode=ParseMode.MARKDOWN)
