
# modules/collection.py - Collection Module (FIXED)

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
from helpers import get_waifu_manager
import config

__MODULE__ = "Collection"
__HELP__ = """
📦 **Collection Commands**

• `/collection` - View your waifu collection
• `/col` - Short alias
• `/fav <id>` - Set favorite waifu
• `/unfav` - Remove favorite
• `/waifuinfo <id>` - View waifu details
"""

ITEMS_PER_PAGE = 8


# ─────────────────────────────────────────────────────────────
#  Helper Functions
# ─────────────────────────────────────────────────────────────

def get_waifu_id(waifu: Dict) -> int:
    """Get waifu ID from any format"""
    # Try all possible ID fields
    wid = (
        waifu.get("waifu_id") or 
        waifu.get("id") or 
        waifu.get("_id") or 
        0
    )
    # Convert to int if string
    try:
        return int(wid)
    except (ValueError, TypeError):
        return 0


def get_waifu_name(waifu: Dict) -> str:
    """Get waifu name from any format"""
    return (
        waifu.get("waifu_name") or 
        waifu.get("name") or 
        "Unknown"
    )


def get_waifu_anime(waifu: Dict) -> str:
    """Get waifu anime from any format"""
    return (
        waifu.get("waifu_anime") or 
        waifu.get("anime") or 
        "Unknown"
    )


def get_waifu_rarity(waifu: Dict) -> str:
    """Get waifu rarity from any format"""
    return (
        waifu.get("waifu_rarity") or 
        waifu.get("rarity") or 
        "common"
    ).lower()


def group_waifus(waifus: List[Dict]) -> List[Dict]:
    """Group same waifus and count them (x2, x3)"""
    if not waifus:
        return []
    
    # Count by waifu_id
    counts = {}
    data = {}
    
    for w in waifus:
        wid = get_waifu_id(w)
        
        # Skip invalid entries
        if wid == 0:
            continue
        
        if wid not in counts:
            counts[wid] = 0
            data[wid] = w
        
        counts[wid] += 1
    
    # Build grouped list with counts
    result = []
    for wid, count in counts.items():
        waifu = data[wid].copy()
        waifu["count"] = count
        waifu["_display_id"] = wid  # Store for display
        result.append(waifu)
    
    # Sort: legendary first, then by count
    rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
    result.sort(key=lambda x: (
        rarity_order.get(get_waifu_rarity(x), 4),
        -x.get("count", 1)
    ))
    
    return result


# ─────────────────────────────────────────────────────────────
#  /collection Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["collection", "mycollection", "col"], prefixes=config.COMMAND_PREFIX))
async def collection_command(client: Client, message: Message):
    user = message.from_user
    await show_collection(message, user.id, page=1, is_callback=False)


async def show_collection(target, user_id: int, page: int = 1, is_callback: bool = False):
    """Show collection with proper grouping"""
    wm = get_waifu_manager()
    
    # Get raw collection from DB
    raw_collection = db.get_full_collection(user_id)
    
    if not raw_collection:
        text = """
📦 **Your Collection**

Your collection is empty! 😢

Use /smash to start collecting waifus!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")]
        ])
        
        if is_callback:
            try:
                if target.message.photo:
                    await target.message.edit_caption(caption=text, reply_markup=buttons)
                else:
                    await target.message.edit_text(text, reply_markup=buttons)
            except MessageNotModified:
                pass
            await target.answer()
        else:
            await target.reply_text(text, reply_markup=buttons)
        return
    
    # Group waifus (removes duplicates, adds count)
    grouped = group_waifus(raw_collection)
    
    # Filter out invalid entries
    grouped = [w for w in grouped if w.get("_display_id", 0) != 0]
    
    total_waifus = len(raw_collection)  # Total including duplicates
    unique_waifus = len(grouped)  # Unique count
    
    # Pagination
    total_pages = max(1, (unique_waifus + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, unique_waifus)
    page_waifus = grouped[start:end]
    
    # Get favorite waifu
    user_data = db.get_user(user_id)
    fav_id = user_data.get("favorite_waifu") if user_data else None
    
    # Build text
    text = f"📦 **Your Collection**\n"
    text += f"📊 {total_waifus} total ({unique_waifus} unique)\n"
    text += f"📄 Page {page}/{total_pages}\n"
    
    # Show favorite at top
    if fav_id:
        fav_waifu = wm.get_waifu_by_id(fav_id)
        if fav_waifu:
            text += f"⭐ Favorite: **{fav_waifu.get('name')}**\n"
    
    text += "\n"
    
    # List waifus
    for w in page_waifus:
        wid = w.get("_display_id", 0)
        name = get_waifu_name(w)
        anime = get_waifu_anime(w)
        rarity = get_waifu_rarity(w)
        count = w.get("count", 1)
        
        emoji = wm.get_rarity_emoji(rarity)
        
        # Format: 🔵 Marin x2 (ID: 1)
        count_str = f" x{count}" if count > 1 else ""
        text += f"{emoji} **{name}**{count_str}\n"
        text += f"   └ {anime} • ID: `{wid}`\n"
    
    # Build keyboard
    buttons = []
    
    # Navigation row
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"col_p_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"col_p_{page+1}"))
    buttons.append(nav_row)
    
    # Filter row
    buttons.append([
        InlineKeyboardButton("🟡 Legendary", callback_data="col_f_legendary"),
        InlineKeyboardButton("🟣 Epic", callback_data="col_f_epic")
    ])
    buttons.append([
        InlineKeyboardButton("🔵 Rare", callback_data="col_f_rare"),
        InlineKeyboardButton("⚪ Common", callback_data="col_f_common")
    ])
    buttons.append([
        InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
        InlineKeyboardButton("🔙 Back", callback_data="start_back")
    ])
    
    # Get image (favorite or first waifu)
    image_url = None
    if fav_id:
        fav_waifu = wm.get_waifu_by_id(fav_id)
        if fav_waifu:
            image_url = fav_waifu.get("image")
    
    if not image_url and page_waifus:
        first_id = page_waifus[0].get("_display_id", 0)
        first_waifu = wm.get_waifu_by_id(first_id)
        if first_waifu:
            image_url = first_waifu.get("image")
    
    # Send/Edit message
    if is_callback:
        try:
            if target.message.photo:
                await target.message.edit_caption(
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await target.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        except MessageNotModified:
            pass
        await target.answer()
    else:
        # Try with image
        if image_url:
            try:
                await target.reply_photo(
                    photo=image_url,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                return
            except:
                pass
        
        await target.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────────────────────
#  Callbacks
# ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^view_collection$"))
async def view_collection_cb(client: Client, callback: CallbackQuery):
    await show_collection(callback, callback.from_user.id, 1, is_callback=True)


@Client.on_callback_query(filters.regex(r"^col_p_(\d+)$"))
async def collection_page_cb(client: Client, callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_collection(callback, callback.from_user.id, page, is_callback=True)


@Client.on_callback_query(filters.regex(r"^col_f_(\w+)$"))
async def collection_filter_cb(client: Client, callback: CallbackQuery):
    """Filter by rarity"""
    rarity = callback.data.split("_")[2]
    user = callback.from_user
    wm = get_waifu_manager()
    
    raw_collection = db.get_full_collection(user.id)
    
    if not raw_collection:
        await callback.answer("Collection empty!", show_alert=True)
        return
    
    # Filter by rarity
    filtered = [w for w in raw_collection if get_waifu_rarity(w) == rarity]
    
    if not filtered:
        await callback.answer(f"No {rarity} waifus!", show_alert=True)
        return
    
    # Group filtered
    grouped = group_waifus(filtered)
    
    emoji = wm.get_rarity_emoji(rarity)
    text = f"{emoji} **{rarity.title()} Waifus** ({len(filtered)} total)\n\n"
    
    for w in grouped[:10]:
        name = get_waifu_name(w)
        wid = w.get("_display_id", 0)
        count = w.get("count", 1)
        count_str = f" x{count}" if count > 1 else ""
        text += f"• **{name}**{count_str} (ID: `{wid}`)\n"
    
    if len(grouped) > 10:
        text += f"\n_...and {len(grouped) - 10} more_"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="view_collection")]
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
async def collection_info_cb(client: Client, callback: CallbackQuery):
    await callback.answer("Use arrows to navigate! ⬅️➡️")


# ─────────────────────────────────────────────────────────────
#  /fav Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["fav", "favorite"], prefixes=config.COMMAND_PREFIX))
async def fav_command(client: Client, message: Message):
    user = message.from_user
    wm = get_waifu_manager()
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/fav <waifu_id>`\n"
            "Example: `/fav 1`"
        )
        return
    
    try:
        waifu_id = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ ID must be a number!")
        return
    
    # Check ownership
    if not db.check_waifu_owned(user.id, waifu_id):
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
        {"$set": {"favorite_waifu": waifu_id}},
        upsert=True
    )
    
    emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    text = f"⭐ **Favorite Set!**\n\n{emoji} **{waifu.get('name')}**"
    
    if waifu.get("image"):
        try:
            await message.reply_photo(photo=waifu["image"], caption=text)
            return
        except:
            pass
    
    await message.reply_text(text)


@Client.on_message(filters.command(["unfav"], prefixes=config.COMMAND_PREFIX))
async def unfav_command(client: Client, message: Message):
    db.users.update_one(
        {"user_id": message.from_user.id},
        {"$unset": {"favorite_waifu": ""}}
    )
    await message.reply_text("✅ Favorite removed!")


# ─────────────────────────────────────────────────────────────
#  /waifuinfo Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["waifuinfo", "wi"], prefixes=config.COMMAND_PREFIX))
async def waifu_info_command(client: Client, message: Message):
    wm = get_waifu_manager()
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/waifuinfo <id>`")
        return
    
    try:
        waifu_id = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ ID must be a number!")
        return
    
    waifu = wm.get_waifu_by_id(waifu_id)
    if not waifu:
        await message.reply_text("❌ Waifu not found!")
        return
    
    emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    
    # Count owned
    collection = db.get_full_collection(user.id)
    owned = sum(1 for w in collection if get_waifu_id(w) == waifu_id)
    owned_str = f"✅ You own x{owned}" if owned > 0 else "❌ Not owned"
    
    text = f"""
{emoji} **{waifu.get('name')}**

📺 {waifu.get('anime')}
💎 {waifu.get('rarity', 'common').title()}
🆔 ID: `{waifu.get('id')}`

{owned_str}
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Favorite", callback_data=f"setfav_{waifu_id}"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ]
    ])
    
    if waifu.get("image"):
        try:
            await message.reply_photo(photo=waifu["image"], caption=text, reply_markup=buttons)
            return
        except:
            pass
    
    await message.reply_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^setfav_(\d+)$"))
async def setfav_callback(client: Client, callback: CallbackQuery):
    waifu_id = int(callback.data.split("_")[1])
    user = callback.from_user
    
    if not db.check_waifu_owned(user.id, waifu_id):
        await callback.answer("❌ You don't own this!", show_alert=True)
        return
    
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {"favorite_waifu": waifu_id}},
        upsert=True
    )
    
    await callback.answer("⭐ Set as favorite!", show_alert=True)
