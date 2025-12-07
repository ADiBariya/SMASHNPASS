# modules/collection.py - Collection Module (Updated)

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.errors import MessageNotModified
from typing import List, Dict
from collections import Counter
from database import db
from helpers import get_waifu_manager, Utils
import config

__MODULE__ = "Collection"
__HELP__ = """
📦 **Collection Commands**

• `/collection` - View your waifu collection
• `/col` - Short alias for collection
• `/fav <waifu_id>` - Set favorite waifu (shows in collection)
• `/unfav` - Remove favorite waifu
• `/waifu <name>` - View specific waifu details
• `/gift <waifu_id>` (reply) - Gift a waifu to someone

Use the inline buttons to navigate pages and filter by rarity.
"""

ITEMS_PER_PAGE = 8


# ─────────────────────────────────────────────────────────────
#  Helper Functions
# ─────────────────────────────────────────────────────────────

def get_user_collection(user_id: int) -> List[Dict]:
    """Get user's collection from database"""
    return db.get_full_collection(user_id)


def group_waifus_by_id(waifus: List[Dict]) -> List[Dict]:
    """Group same waifus and add count (x2, x3, etc.)"""
    # Count waifus by ID
    waifu_counts = Counter()
    waifu_data = {}
    
    for w in waifus:
        waifu_id = w.get("waifu_id") or w.get("id") or 0
        waifu_counts[waifu_id] += 1
        
        # Store waifu data (keep first occurrence)
        if waifu_id not in waifu_data:
            waifu_data[waifu_id] = w
    
    # Build grouped list
    grouped = []
    for waifu_id, count in waifu_counts.items():
        if waifu_id in waifu_data:
            waifu = waifu_data[waifu_id].copy()
            waifu["count"] = count
            grouped.append(waifu)
    
    # Sort by rarity (legendary first) then by count
    rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
    grouped.sort(key=lambda x: (
        rarity_order.get(x.get("waifu_rarity", "common").lower(), 4),
        -x.get("count", 1)
    ))
    
    return grouped


def get_waifu_display_name(waifu: Dict) -> str:
    """Get waifu name with proper fallback for traded waifus"""
    # Try different name fields
    name = (
        waifu.get("waifu_name") or 
        waifu.get("name") or 
        "Unknown"
    )
    return name


def get_waifu_display_id(waifu: Dict) -> int:
    """Get waifu ID"""
    return waifu.get("waifu_id") or waifu.get("id") or 0


# ─────────────────────────────────────────────────────────────
#  /collection Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["collection", "mycollection", "col"], prefixes=config.COMMAND_PREFIX))
async def collection_command(client: Client, message: Message):
    user = message.from_user
    await show_collection_message(message, user.id, page=1)


async def show_collection_message(message: Message, user_id: int, page: int = 1):
    wm = get_waifu_manager()
    
    # Get all waifus
    all_waifus = get_user_collection(user_id)
    
    if not all_waifus:
        text = """
📦 **Your Collection**

Your collection is empty! 😢

Use /smash to start collecting waifus!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")]
        ])
        await message.reply_text(text, reply_markup=buttons)
        return
    
    # Group waifus (x2, x3 format)
    grouped_waifus = group_waifus_by_id(all_waifus)
    total_unique = len(grouped_waifus)
    total_waifus = len(all_waifus)
    
    # Pagination
    total_pages = (total_unique + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total_unique)
    page_waifus = grouped_waifus[start:end]
    
    # Build text
    text = f"📦 **Your Collection**\n"
    text += f"📊 {total_waifus} waifus ({total_unique} unique)\n"
    text += f"📄 Page {page}/{total_pages}\n\n"
    
    for w in page_waifus:
        name = get_waifu_display_name(w)
        waifu_id = get_waifu_display_id(w)
        rarity = w.get("waifu_rarity") or w.get("rarity", "common")
        count = w.get("count", 1)
        
        rarity_emoji = wm.get_rarity_emoji(rarity)
        
        # Show count if more than 1
        count_text = f" **x{count}**" if count > 1 else ""
        
        text += f"{rarity_emoji} **{name}**{count_text}\n"
        text += f"   └ ID: `{waifu_id}`\n"
    
    # Get favorite waifu for image
    user_data = db.get_user(user_id)
    fav_waifu_id = user_data.get("favorite_waifu") if user_data else None
    
    buttons = build_collection_keyboard(page, total_pages)
    
    # Send with favorite waifu image or random waifu image
    image_url = None
    
    if fav_waifu_id:
        # Get favorite waifu image
        fav_waifu = wm.get_waifu_by_id(fav_waifu_id)
        if fav_waifu:
            image_url = fav_waifu.get("image")
            text = f"⭐ **Favorite:** {fav_waifu.get('name')}\n\n" + text
    else:
        # Get random waifu from collection for image
        if grouped_waifus:
            random_waifu_id = get_waifu_display_id(grouped_waifus[0])
            random_waifu = wm.get_waifu_by_id(random_waifu_id)
            if random_waifu:
                image_url = random_waifu.get("image")
    
    # Send with image
    if image_url:
        try:
            await message.reply_photo(
                photo=image_url,
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        except Exception as e:
            print(f"⚠️ Collection image failed: {e}")
    
    # Fallback to text only
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────────────────────
#  Callback Handlers
# ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^view_collection$"))
async def view_collection_callback(client: Client, callback: CallbackQuery):
    user = callback.from_user
    await show_collection_callback(callback, user.id, page=1)


@Client.on_callback_query(filters.regex(r"^col_page_(\d+)$"))
async def collection_page_callback(client: Client, callback: CallbackQuery):
    user = callback.from_user
    page = int(callback.data.split("_")[2])
    await show_collection_callback(callback, user.id, page)


async def show_collection_callback(callback: CallbackQuery, user_id: int, page: int = 1):
    wm = get_waifu_manager()
    
    all_waifus = get_user_collection(user_id)
    
    if not all_waifus:
        text = """
📦 **Your Collection**

Your collection is empty! 😢

Use /smash to start collecting waifus!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
        ])
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                await callback.message.edit_text(text, reply_markup=buttons)
        except MessageNotModified:
            pass
        
        await callback.answer()
        return
    
    # Group waifus
    grouped_waifus = group_waifus_by_id(all_waifus)
    total_unique = len(grouped_waifus)
    total_waifus = len(all_waifus)
    
    # Pagination
    total_pages = (total_unique + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total_unique)
    page_waifus = grouped_waifus[start:end]
    
    # Build text
    text = f"📦 **Your Collection**\n"
    text += f"📊 {total_waifus} waifus ({total_unique} unique)\n"
    text += f"📄 Page {page}/{total_pages}\n\n"
    
    for w in page_waifus:
        name = get_waifu_display_name(w)
        waifu_id = get_waifu_display_id(w)
        rarity = w.get("waifu_rarity") or w.get("rarity", "common")
        count = w.get("count", 1)
        
        rarity_emoji = wm.get_rarity_emoji(rarity)
        count_text = f" **x{count}**" if count > 1 else ""
        
        text += f"{rarity_emoji} **{name}**{count_text}\n"
        text += f"   └ ID: `{waifu_id}`\n"
    
    # Get favorite waifu
    user_data = db.get_user(user_id)
    fav_waifu_id = user_data.get("favorite_waifu") if user_data else None
    
    if fav_waifu_id:
        fav_waifu = wm.get_waifu_by_id(fav_waifu_id)
        if fav_waifu:
            text = f"⭐ **Favorite:** {fav_waifu.get('name')}\n\n" + text
    
    buttons = build_collection_keyboard(page, total_pages)
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=text, 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await callback.message.edit_text(
                text, 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except MessageNotModified:
        pass
    except Exception as e:
        print(f"⚠️ Collection edit error: {e}")
    
    await callback.answer()


def build_collection_keyboard(page: int, total_pages: int):
    buttons = []
    nav_row = []
    
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="col_info"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_page_{page+1}"))
    
    buttons.append(nav_row)
    
    # Rarity filters
    buttons.append([
        InlineKeyboardButton("🟡 Legendary", callback_data="col_filter_legendary"),
        InlineKeyboardButton("🟣 Epic", callback_data="col_filter_epic")
    ])
    buttons.append([
        InlineKeyboardButton("🔵 Rare", callback_data="col_filter_rare"),
        InlineKeyboardButton("⚪ Common", callback_data="col_filter_common")
    ])
    buttons.append([
        InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
        InlineKeyboardButton("🔙 Back", callback_data="start_back")
    ])
    
    return buttons


# ─────────────────────────────────────────────────────────────
#  Filter Callback
# ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^col_filter_(\w+)$"))
async def collection_filter_callback(client: Client, callback: CallbackQuery):
    rarity = callback.data.split("_")[2]
    user = callback.from_user
    wm = get_waifu_manager()
    
    all_waifus = get_user_collection(user.id)
    
    if not all_waifus:
        await callback.answer("Your collection is empty!", show_alert=True)
        return
    
    # Filter by rarity
    filtered = [w for w in all_waifus 
                if (w.get("waifu_rarity") or w.get("rarity", "common")).lower() == rarity.lower()]
    
    if not filtered:
        await callback.answer(f"No {rarity} waifus in your collection!", show_alert=True)
        return
    
    # Group filtered waifus
    grouped = group_waifus_by_id(filtered)
    
    rarity_emoji = wm.get_rarity_emoji(rarity)
    text = f"{rarity_emoji} **Your {rarity.title()} Waifus** ({len(filtered)} total)\n\n"
    
    for w in grouped[:10]:
        name = get_waifu_display_name(w)
        waifu_id = get_waifu_display_id(w)
        count = w.get("count", 1)
        count_text = f" **x{count}**" if count > 1 else ""
        
        text += f"• **{name}**{count_text} (ID: `{waifu_id}`)\n"
    
    if len(grouped) > 10:
        text += f"\n_...and {len(grouped) - 10} more unique waifus_"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Collection", callback_data="view_collection")]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except MessageNotModified:
        pass
    
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^col_info$"))
async def collection_info_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Use arrows to navigate pages! ⬅️ ➡️")


# ─────────────────────────────────────────────────────────────
#  /fav Command - Set Favorite Waifu
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["fav", "favorite", "setfav"], prefixes=config.COMMAND_PREFIX))
async def set_favorite_command(client: Client, message: Message):
    user = message.from_user
    wm = get_waifu_manager()
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/fav <waifu_id>`\n\n"
            "Example: `/fav 5`\n\n"
            "Use `/collection` to see waifu IDs."
        )
        return
    
    try:
        waifu_id = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ Invalid waifu ID! Must be a number.")
        return
    
    # Check if user owns this waifu
    owned = db.check_waifu_owned(user.id, waifu_id)
    
    if not owned:
        await message.reply_text("❌ You don't own this waifu!")
        return
    
    # Get waifu info
    waifu = wm.get_waifu_by_id(waifu_id)
    
    if not waifu:
        await message.reply_text("❌ Waifu not found!")
        return
    
    # Set favorite
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {"favorite_waifu": waifu_id}}
    )
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    
    text = f"""
⭐ **Favorite Waifu Set!**

{rarity_emoji} **{waifu.get('name')}**
📺 {waifu.get('anime')}

Your favorite waifu will now appear in your collection!
"""
    
    image_url = waifu.get("image")
    
    if image_url:
        try:
            await message.reply_photo(photo=image_url, caption=text)
            return
        except:
            pass
    
    await message.reply_text(text)


@Client.on_message(filters.command(["unfav", "removefav"], prefixes=config.COMMAND_PREFIX))
async def remove_favorite_command(client: Client, message: Message):
    user = message.from_user
    
    # Remove favorite
    db.users.update_one(
        {"user_id": user.id},
        {"$unset": {"favorite_waifu": ""}}
    )
    
    await message.reply_text("✅ Favorite waifu removed!")


# ─────────────────────────────────────────────────────────────
#  /waifu Info
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["waifuinfo", "wi"], prefixes=config.COMMAND_PREFIX))
async def waifu_info_command(client: Client, message: Message):
    wm = get_waifu_manager()
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/waifuinfo <name or id>`\n\n"
            "Example: `/waifuinfo Hinata` or `/waifuinfo 5`"
        )
        return
    
    query = " ".join(message.command[1:])
    
    # Try to find by ID first
    waifu = None
    try:
        waifu_id = int(query)
        waifu = wm.get_waifu_by_id(waifu_id)
    except ValueError:
        # Not a number, search by name
        waifu = wm.get_waifu_by_name(query)
    
    if not waifu:
        results = wm.search_waifus(query)
        if results:
            text = f"🔍 **Search Results for '{query}':**\n\n"
            for w in results[:5]:
                rarity_emoji = wm.get_rarity_emoji(w.get("rarity", "common"))
                text += f"{rarity_emoji} {w.get('name')} (ID: {w.get('id')}) - {w.get('anime')}\n"
            await message.reply_text(text)
        else:
            await message.reply_text(f"❌ Waifu '{query}' not found!")
        return
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    
    # Check ownership
    owned = db.check_waifu_owned(user.id, waifu.get("id"))
    
    # Count how many user owns
    user_collection = get_user_collection(user.id)
    owned_count = sum(1 for w in user_collection 
                      if (w.get("waifu_id") or w.get("id")) == waifu.get("id"))
    
    owned_text = f"✅ You own **x{owned_count}**" if owned_count > 0 else "❌ Not in your collection"
    
    text = f"""
{rarity_emoji} **{waifu.get('name')}**

📺 **Anime:** {waifu.get('anime')}
💎 **Rarity:** {waifu.get('rarity', 'common').title()}
🆔 **ID:** {waifu.get('id')}

{owned_text}
"""
    
    image_url = waifu.get("image")
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Set Favorite", callback_data=f"setfav_{waifu.get('id')}"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ]
    ])
    
    if image_url:
        try:
            await message.reply_photo(photo=image_url, caption=text, reply_markup=buttons)
            return
        except:
            pass
    
    await message.reply_text(text, reply_markup=buttons)


# ─────────────────────────────────────────────────────────────
#  Set Favorite Callback
# ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^setfav_(\d+)$"))
async def set_favorite_callback(client: Client, callback: CallbackQuery):
    user = callback.from_user
    waifu_id = int(callback.data.split("_")[1])
    
    # Check ownership
    owned = db.check_waifu_owned(user.id, waifu_id)
    
    if not owned:
        await callback.answer("❌ You don't own this waifu!", show_alert=True)
        return
    
    # Set favorite
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {"favorite_waifu": waifu_id}}
    )
    
    await callback.answer("⭐ Set as favorite!", show_alert=True)


# ─────────────────────────────────────────────────────────────
#  /gift Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["gift", "give"], prefixes=config.COMMAND_PREFIX))
async def gift_waifu_command(client: Client, message: Message):
    user = message.from_user
    wm = get_waifu_manager()
    
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Usage:** Reply to someone's message with:\n"
            "`/gift <waifu_id>`\n\n"
            "Example: Reply to a user and type `/gift 5`"
        )
        return
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please specify the waifu ID!\n`/gift <waifu_id>`")
        return
    
    try:
        waifu_id = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ Invalid waifu ID!")
        return
    
    target_user = message.reply_to_message.from_user
    
    if target_user.id == user.id:
        await message.reply_text("❌ You can't gift to yourself!")
        return
    
    if target_user.is_bot:
        await message.reply_text("❌ You can't gift to a bot!")
        return
    
    # Check ownership
    waifu_in_collection = db.get_waifu_from_collection(user.id, waifu_id)
    
    if not waifu_in_collection:
        await message.reply_text("❌ You don't own this waifu!")
        return
    
    # Get full waifu info for proper transfer
    full_waifu = wm.get_waifu_by_id(waifu_id)
    
    if not full_waifu:
        await message.reply_text("❌ Waifu data not found!")
        return
    
    # Ensure target exists
    db.get_or_create_user(target_user.id, target_user.username, target_user.first_name)
    
    # Remove from sender
    db.remove_from_collection(user.id, waifu_id)
    
    # Add to receiver with FULL data (not Unknown)
    db.add_to_collection(target_user.id, full_waifu)
    
    waifu_name = full_waifu.get("name", "Unknown")
    rarity_emoji = wm.get_rarity_emoji(full_waifu.get("rarity", "common"))
    
    await message.reply_text(
        f"🎁 **Gift Successful!**\n\n"
        f"{rarity_emoji} **{waifu_name}** has been gifted to "
        f"{Utils.mention_user(target_user.id, target_user.first_name)}!"
    )
