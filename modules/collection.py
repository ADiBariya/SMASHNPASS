# modules/collection.py - Collection & Trade Module (FIXED FORMAT)

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultPhoto
)
from pyrogram.errors import MessageNotModified
from typing import List, Dict
from database import db
from helpers import get_waifu_manager
import config
from datetime import datetime, timedelta
import re

__MODULE__ = "𝐂𝐨𝐥𝐥𝐞𝐜𝐭𝐢𝐨𝐧"
__HELP__ = """
📦 **Collection Commands**
• `/collection` - View your waifu collection
• `/col` - Short alias
• `/fav <id>` - Set favorite waifu
• `/unfav` - Remove favorite
• `/waifuinfo <id>` - View waifu details

🔄 **Trade Commands**
• `/trade @user` - Start a trade
• `/mytrades` - View pending trades
• `/canceltrade` - Cancel your trade

📱 **Inline Mode**
• `@botusername user_waifus.USER_ID` - View collection as photos
"""

ITEMS_PER_PAGE = 8
INLINE_PHOTO_LIMIT = 50

# Trade storage
active_trades = {}
trade_cooldowns = {}

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"📦 [COL/TRADE] {msg}")

def get_waifu_id(waifu: Dict) -> int:
    wid = (
        waifu.get("waifu_id") or 
        waifu.get("id") or 
        waifu.get("_id") or 
        0
    )
    try:
        return int(wid)
    except (ValueError, TypeError):
        return 0


def get_waifu_name(waifu: Dict) -> str:
    return (
        waifu.get("waifu_name") or 
        waifu.get("name") or 
        "Unknown"
    )


def get_waifu_anime(waifu: Dict) -> str:
    return (
        waifu.get("waifu_anime") or 
        waifu.get("anime") or 
        "Unknown"
    )


def get_waifu_rarity(waifu: Dict) -> str:
    return str(
        waifu.get("waifu_rarity") or 
        waifu.get("rarity") or 
        "common"
    ).lower()


def get_waifu_image(waifu: Dict) -> str:
    return (
        waifu.get("waifu_image") or 
        waifu.get("image") or 
        ""
    )


def get_rarity_emoji(rarity: str) -> str:
    return {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(rarity).lower(), "⚪")


def format_waifu_trade(waifu: Dict) -> str:
    if not waifu:
        return "❓ Unknown"
    
    emoji = get_rarity_emoji(get_waifu_rarity(waifu))
    name = get_waifu_name(waifu)
    anime = get_waifu_anime(waifu)
    wid = get_waifu_id(waifu)
    rarity = get_waifu_rarity(waifu).title()
    
    return f"{emoji} **{name}**\n📺 {anime}\n💎 {rarity}\n🆔 `{wid}`"


def group_waifus_by_variant(waifus: List[Dict]) -> List[Dict]:
    if not waifus:
        return []
    
    variant_counts = {}
    variant_data = {}
    
    for w in waifus:
        wid = get_waifu_id(w)
        if wid == 0:
            continue
        
        image = get_waifu_image(w)
        variant_key = f"{wid}||{image}"
        
        if variant_key not in variant_counts:
            variant_counts[variant_key] = 0
            variant_data[variant_key] = w.copy()
        
        variant_counts[variant_key] += 1
    
    result = []
    for variant_key, count in variant_counts.items():
        waifu = variant_data[variant_key].copy()
        waifu["count"] = count
        waifu["_display_id"] = get_waifu_id(waifu)
        waifu["_variant_key"] = variant_key
        result.append(waifu)
    
    rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
    result.sort(key=lambda x: (
        rarity_order.get(get_waifu_rarity(x), 4),
        -x.get("count", 1),
        get_waifu_name(x).lower()
    ))
    
    return result


def get_unique_variants(collection: List[Dict], limit: int = 10) -> List[Dict]:
    seen_keys = set()
    unique = []
    
    for w in collection:
        wid = get_waifu_id(w)
        if wid == 0:
            continue
        
        image = get_waifu_image(w)
        variant_key = f"{wid}||{image}"
        
        if variant_key not in seen_keys:
            seen_keys.add(variant_key)
            unique.append(w)
        
        if len(unique) >= limit:
            break
    
    return unique


async def safe_edit(client, chat_id, msg_id, text, buttons=None):
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=buttons
        )
        return True
    except:
        return False


async def safe_send(client, chat_id, text, buttons=None):
    try:
        return await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=buttons
        )
    except:
        return None

@Client.on_inline_query()
async def inline_collection_handler(client: Client, inline_query: InlineQuery):
    """
    Handle inline queries
    Format: @botusername user_waifus.USER_ID
    Example: @Horikita_Robot user_waifus.1432702628
    """
    user = inline_query.from_user
    query = inline_query.query.strip()
    
    debug(f"═══════════════════════════════════════")
    debug(f"INLINE from {user.first_name} ({user.id})")
    debug(f"Query: '{query}'")
    debug(f"═══════════════════════════════════════")
    
    # Check if query matches user_waifus.USER_ID pattern
    match = re.match(r'^user_waifus\.(\d+)$', query)
    
    if not match:
        # Show help message if format is wrong
        bot = await client.get_me()
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="help",
                    title="📦 How to use Inline Collection",
                    description="Type: user_waifus.YOUR_USER_ID",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📦 **Inline Collection Usage**\n\n"
                        f"Format: `@{bot.username} user_waifus.USER_ID`\n\n"
                        f"Example: `@{bot.username} user_waifus.{user.id}`\n\n"
                        f"💡 Your User ID: `{user.id}`"
                    )
                ),
                InlineQueryResultArticle(
                    id="my_collection",
                    title=f"📸 View Your Collection",
                    description=f"Type: user_waifus.{user.id}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📦 To view your collection inline:\n\n"
                        f"`@{bot.username} user_waifus.{user.id}`"
                    )
                )
            ],
            cache_time=5,
            is_personal=True
        )
        return
    
    # Extract user ID from query
    target_user_id = int(match.group(1))
    debug(f"Target User ID: {target_user_id}")
    
    # Get collection from database
    collection = db.get_full_collection(target_user_id)
    debug(f"Collection size: {len(collection) if collection else 0}")
    
    # Empty collection
    if not collection:
        debug("Collection EMPTY!")
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="empty",
                    title="📦 Collection Empty!",
                    description=f"User {target_user_id} has no waifus",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📦 **Collection Empty!**\n\n"
                        f"User `{target_user_id}` has no waifus yet!\n\n"
                        f"Use /smash to start collecting!"
                    )
                )
            ],
            cache_time=10,
            is_personal=True
        )
        return
    
    # Group duplicates
    grouped = group_waifus_by_variant(collection)
    debug(f"Grouped: {len(grouped)} unique waifus")
    
    # Get user data for favorites
    user_data = db.get_user(target_user_id)
    fav_id = user_data.get("favorite_waifu") if user_data else None
    
    # Build photo results
    results = []
    
    for i, w in enumerate(grouped[:INLINE_PHOTO_LIMIT]):
        image = get_waifu_image(w)
        
        # Validate image URL
        if not image or not image.startswith("http"):
            debug(f"Skip {i}: invalid image")
            continue
        
        wid = get_waifu_id(w)
        name = get_waifu_name(w)
        anime = get_waifu_anime(w)
        rarity = get_waifu_rarity(w)
        count = w.get("count", 1)
        emoji = get_rarity_emoji(rarity)
        is_fav = "⭐ " if fav_id and fav_id == wid else ""
        
        # Build caption (plain text - no parse_mode issues)
        caption = f"{emoji} {is_fav}{name}\n"
        caption += f"━━━━━━━━━━━━━━━\n"
        caption += f"📺 Anime: {anime}\n"
        caption += f"💎 Rarity: {rarity.title()}\n"
        caption += f"🆔 ID: {wid}\n"
        caption += f"📦 Owned: x{count}"
        
        result_id = f"waifu_{target_user_id}_{wid}_{i}"
        
        # Add photo result (try both Pyrogram versions)
        try:
            results.append(
                InlineQueryResultPhoto(
                    id=result_id,
                    photo_url=image,
                    thumbnail_url=image,
                    caption=caption
                )
            )
            debug(f"Added: {name}")
        except TypeError:
            try:
                results.append(
                    InlineQueryResultPhoto(
                        id=result_id,
                        photo_url=image,
                        thumb_url=image,
                        caption=caption
                    )
                )
                debug(f"Added (v1): {name}")
            except Exception as e:
                debug(f"Error: {e}")
                continue
        except Exception as e:
            debug(f"Error: {e}")
            continue
    
    debug(f"Total photo results: {len(results)}")
    
    # If no valid photos, show text fallback
    if not results:
        debug("No photos, creating text fallback")
        text = f"📦 Collection of User {target_user_id}\n\n"
        text += f"Total: {len(grouped)} unique waifus\n\n"
        for w in grouped[:15]:
            emoji = get_rarity_emoji(get_waifu_rarity(w))
            name = get_waifu_name(w)
            count = w.get("count", 1)
            text += f"{emoji} {name}"
            if count > 1:
                text += f" (x{count})"
            text += "\n"
        
        if len(grouped) > 15:
            text += f"\n...and {len(grouped) - 15} more!"
        
        results = [
            InlineQueryResultArticle(
                id="text_fallback",
                title=f"📦 Collection ({len(grouped)} waifus)",
                description="No valid images found",
                input_message_content=InputTextMessageContent(message_text=text)
            )
        ]
    
    # Answer inline query
    try:
        await inline_query.answer(
            results=results,
            cache_time=30,
            is_personal=False,
            switch_pm_text=f"📦 {len(collection)} waifus found!",
            switch_pm_parameter="start"
        )
        debug("✅ Answered successfully!")
    except Exception as e:
        debug(f"❌ Error answering: {e}")
        try:
            await inline_query.answer(results=results[:20], cache_time=10, is_personal=False)
            debug("✅ Answered with limited results")
        except Exception as e2:
            debug(f"❌ Fallback failed: {e2}")

@Client.on_message(filters.command(["collection", "mycollection", "col"], prefixes=config.COMMAND_PREFIX))
async def collection_command(client: Client, message: Message):
    user = message.from_user
    debug(f"Collection command from {user.id}")
    await show_collection(client, message, user.id, page=1, is_callback=False)


async def show_collection(client, target, user_id: int, page: int = 1, is_callback: bool = False, rarity_filter: str = None):
    """Show collection with variant-based grouping"""
    wm = get_waifu_manager()
    
    # Get raw collection
    raw_collection = db.get_full_collection(user_id)
    
    if not raw_collection:
        text = """
📦 **Your Collection**

Your collection is empty!

Use /smash to start collecting waifus!
"""     
        if is_callback:
            try:
                if target.message.photo:
                    await target.message.edit_caption(caption=text)
                else:
                    await target.message.edit_text(text)
            except MessageNotModified:
                pass
            await target.answer()
        else:
            await target.reply_text(text)
        return
    
    # Apply rarity filter if specified
    if rarity_filter:
        filtered = [w for w in raw_collection if get_waifu_rarity(w) == rarity_filter]
        if not filtered:
            if is_callback:
                await target.answer(f"No {rarity_filter} waifus!", show_alert=True)
            return
        working_collection = filtered
    else:
        working_collection = raw_collection
    
    # Group by variant (ID + Image)
    grouped = group_waifus_by_variant(working_collection)
    grouped = [w for w in grouped if w.get("_display_id", 0) != 0]
    
    total_waifus = len(working_collection)
    unique_variants = len(grouped)
    
    # Pagination
    total_pages = max(1, (unique_variants + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, unique_variants)
    page_waifus = grouped[start:end]
    
    # Get favorite
    user_data = db.get_user(user_id)
    fav_id = user_data.get("favorite_waifu") if user_data else None
    
    # Build text
    if rarity_filter:
        emoji = get_rarity_emoji(rarity_filter)
        text = f"{emoji} **{rarity_filter.title()} Collection**\n\n"
    else:
        text = "📦 **Waifu Collection**\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 Total: {total_waifus} | Page {page}/{total_pages}\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Display waifus
    for w in page_waifus:
        wid = w.get("_display_id", 0)
        name = get_waifu_name(w)
        anime = get_waifu_anime(w)
        rarity = get_waifu_rarity(w)
        count = w.get("count", 1)
        
        emoji = get_rarity_emoji(rarity)
        
        # Check if favorite
        is_fav = "⭐ " if fav_id and fav_id == wid else ""
        
        # Format with count if more than 1
        if count > 1:
            text += f"{emoji} {is_fav}**{name}** (x{count})\n"
        else:
            text += f"{emoji} {is_fav}**{name}**\n"
        
        text += f"   ┗ 📺 {anime} | 🆔 `{wid}`\n\n"
    
    # Buttons
    buttons = []
    
    # Navigation
    nav_row = []
    if rarity_filter:
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"colf_{rarity_filter}_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"colf_{rarity_filter}_{page+1}"))
    else:
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"col_p_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"col_p_{page+1}"))

    if nav_row:
        buttons.append(nav_row)
    
    # Rarity filters
    buttons.append([
        InlineKeyboardButton(
            "🟡✓" if rarity_filter == "legendary" else "🟡",
            callback_data="col_f_legendary"
        ),
        InlineKeyboardButton(
            "🟣✓" if rarity_filter == "epic" else "🟣",
            callback_data="col_f_epic"
        ),
        InlineKeyboardButton(
            "🔵✓" if rarity_filter == "rare" else "🔵",
            callback_data="col_f_rare"
        ),
        InlineKeyboardButton(
            "⚪✓" if rarity_filter == "common" else "⚪",
            callback_data="col_f_common"
        )
    ])
    
    # Bottom buttons
    if rarity_filter:
        buttons.append([
            InlineKeyboardButton("📦 ALL", callback_data="view_collection")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("📊 LEADEROARD", callback_data="lb_collection")
        ])
    
    # Inline gallery button
    buttons.append([
        InlineKeyboardButton("📸 Photo Gallery", switch_inline_query_current_chat=f"user_waifus.{user_id}")
    ])
    
    # Get image for display
    image_url = None
    if fav_id:
        fav_waifu = wm.get_waifu_by_id(fav_id)
        if fav_waifu:
            image_url = fav_waifu.get("image")
    
    if not image_url and page_waifus:
        image_url = get_waifu_image(page_waifus[0])
    
    # Send/Edit
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

@Client.on_callback_query(filters.regex(r"^view_collection$"))
async def view_collection_cb(client: Client, callback: CallbackQuery):
    debug(f"view_collection callback from {callback.from_user.id}")
    await show_collection(client, callback, callback.from_user.id, 1, is_callback=True)

@Client.on_callback_query(filters.regex(r"^col_p_(\d+)$"))
async def collection_page_cb(client, callback):
    page = int(callback.data.split("_")[2])

    # OWNER CHECK
    owner_id = callback.message.reply_to_message.from_user.id \
        if callback.message.reply_to_message else callback.from_user.id

    if callback.from_user.id != owner_id:
        return await callback.answer("❌ This is not your collection!", show_alert=True)

    await show_collection(client, callback, owner_id, page, is_callback=True)

@Client.on_callback_query(filters.regex(r"^col_f_(\w+)$"))
async def collection_filter_cb(client, callback):
    rarity = callback.data.split("_")[2]

    owner_id = callback.message.reply_to_message.from_user.id \
        if callback.message.reply_to_message else callback.from_user.id

    if callback.from_user.id != owner_id:
        return await callback.answer("❌ Not your collection!", show_alert=True)

    await show_collection(client, callback, owner_id, 1, is_callback=True, rarity_filter=rarity)

@Client.on_callback_query(filters.regex(r"^colf_(\w+)_(\d+)$"))
async def collection_filter_page_cb(client, callback):
    parts = callback.data.split("_")
    rarity = parts[1]
    page = int(parts[2])

    owner_id = callback.message.reply_to_message.from_user.id \
        if callback.message.reply_to_message else callback.from_user.id

    if callback.from_user.id != owner_id:
        return await callback.answer("❌ Not your collection!", show_alert=True)

    await show_collection(client, callback, owner_id, page, is_callback=True, rarity_filter=rarity)

@Client.on_callback_query(filters.regex(r"^col_info$"))
async def collection_info_cb(client: Client, callback: CallbackQuery):
    await callback.answer("Use arrows to navigate! ⬅️➡️")

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
    
    if not db.check_waifu_owned(user.id, waifu_id):
        await message.reply_text("❌ You don't own this waifu!")
        return
    
    waifu = wm.get_waifu_by_id(waifu_id)
    if not waifu:
        await message.reply_text("❌ Waifu not found!")
        return
    
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {"favorite_waifu": waifu_id}},
        upsert=True
    )
    
    emoji = get_rarity_emoji(waifu.get("rarity", "common"))
    text = f"⭐ **Favorite Set!**\n\n{emoji} **{waifu.get('name')}** - `{waifu.get('id')}`"
    
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
    
    emoji = get_rarity_emoji(waifu.get("rarity", "common"))
    
    collection = db.get_full_collection(user.id)
    owned = sum(1 for w in collection if get_waifu_id(w) == waifu_id) if collection else 0
    
    if owned > 1:
        owned_str = f"✅ You own (x{owned})"
    elif owned == 1:
        owned_str = "✅ You own this"
    else:
        owned_str = "❌ Not owned"
    
    text = f"""
{emoji} **{waifu.get('name')}**

📺 {waifu.get('anime')}
💎 {waifu.get('rarity', 'common').title()}
🆔 `{waifu.get('id')}`

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

@Client.on_message(filters.command(["trade", "tr"], prefixes=config.COMMAND_PREFIX))
async def trade_command(client: Client, message: Message):
    """Start a trade with another user"""
    user = message.from_user
    debug(f"Trade from {user.first_name} ({user.id})")
    
    # Cooldown check
    if user.id in trade_cooldowns:
        remaining = (trade_cooldowns[user.id] - datetime.now()).total_seconds()
        if remaining > 0:
            await message.reply_text(f"⏳ Wait {int(remaining)}s before trading again!")
            return
    
    # Get target user
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) >= 2:
        try:
            target = await client.get_users(message.command[1])
        except:
            await message.reply_text("❌ User not found!")
            return
    else:
        await message.reply_text(
            "❌ **How to trade:**\n"
            "• Reply to user: `/trade`\n"
            "• Or: `/trade @username`"
        )
        return
    
    # Validations
    if not target:
        await message.reply_text("❌ User not found!")
        return
    if target.id == user.id:
        await message.reply_text("❌ Can't trade with yourself!")
        return
    if target.is_bot:
        await message.reply_text("❌ Can't trade with bots!")
        return
    
    # Check existing trade
    for t in active_trades.values():
        if t["sender_id"] == user.id:
            await message.reply_text("❌ You have an active trade!\nUse /canceltrade first.")
            return
    
    # Get collection
    collection = db.get_full_collection(user.id)
    debug(f"Collection: {len(collection) if collection else 0} waifus")
    
    if not collection:
        await message.reply_text("❌ You have no waifus!\nPlay /smash first!")
        return
    
    # Create trade
    trade_id = f"{user.id % 100000}{int(datetime.now().timestamp()) % 100000}"
    debug(f"Trade ID: {trade_id}")
    
    # Get unique variants (by ID + image)
    unique_waifus = get_unique_variants(collection, 10)
    
    active_trades[trade_id] = {
        "sender_id": user.id,
        "sender_name": user.first_name,
        "receiver_id": target.id,
        "receiver_name": target.first_name,
        "sender_waifu": None,
        "receiver_waifu": None,
        "sender_waifus": unique_waifus,
        "receiver_waifus": [],
        "sender_ok": False,
        "receiver_ok": False,
        "status": "picking",
        "chat_id": message.chat.id,
        "msg_id": None,
        "recv_chat_id": None,
        "recv_msg_id": None
    }
    
    # Build buttons
    buttons = []
    row = []
    for i, w in enumerate(unique_waifus):
        name = get_waifu_name(w)[:12]
        row.append(InlineKeyboardButton(name, callback_data=f"tw_{trade_id}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")])
    
    text = f"""
💘 **New Trade**

**From:** {user.mention}
**To:** {target.mention}

📦 Select a waifu to offer:
"""
    
    try:
        sent = await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        active_trades[trade_id]["msg_id"] = sent.id
    except Exception as e:
        del active_trades[trade_id]
        await message.reply_text(f"❌ Error: {e}")
        return
    
    trade_cooldowns[user.id] = datetime.now() + timedelta(seconds=30)


@Client.on_callback_query(filters.regex(r"^tw_(\d+)_(\d+)$"))
async def sender_select_cb(client: Client, callback: CallbackQuery):
    """Sender picks waifu"""
    user = callback.from_user
    parts = callback.data.split("_")
    trade_id = parts[1]
    waifu_idx = int(parts[2])
    
    debug(f"Sender select: trade={trade_id}, idx={waifu_idx}")
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if trade["sender_id"] != user.id:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    if trade["status"] != "picking":
        await callback.answer("❌ Already selected!", show_alert=True)
        return
    
    sender_waifus = trade.get("sender_waifus", [])
    if waifu_idx >= len(sender_waifus):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = sender_waifus[waifu_idx]
    trade["sender_waifu"] = selected
    trade["status"] = "waiting"
    
    debug(f"Sender selected: {get_waifu_name(selected)} (ID: {get_waifu_id(selected)})")
    
    waifu_text = format_waifu_trade(selected)
    
    # Update sender message
    try:
        await callback.message.edit_text(
            f"💘 **Trade in Progress**\n\n"
            f"**You offer:**\n{waifu_text}\n\n"
            f"⏳ Waiting for **{trade['receiver_name']}**...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")]
            ])
        )
    except:
        pass
    
    # Get receiver collection
    recv_collection = db.get_full_collection(trade["receiver_id"])
    if not recv_collection:
        await callback.message.edit_text(f"❌ {trade['receiver_name']} has no waifus!")
        del active_trades[trade_id]
        return
    
    # Get unique variants for receiver
    unique_recv = get_unique_variants(recv_collection, 10)
    trade["receiver_waifus"] = unique_recv
    
    # Build receiver buttons
    recv_buttons = []
    row = []
    for i, w in enumerate(unique_recv):
        name = get_waifu_name(w)[:12]
        row.append(InlineKeyboardButton(name, callback_data=f"tr_{trade_id}_{i}"))
        if len(row) == 2:
            recv_buttons.append(row)
            row = []
    if row:
        recv_buttons.append(row)
    recv_buttons.append([InlineKeyboardButton("❌ Decline", callback_data=f"tc_{trade_id}")])
    
    recv_text = f"""
💘 **Trade Request!**

**From:** {trade['sender_name']}

**They offer:**
{waifu_text}

📦 Select your waifu:
"""
    
    # Send to receiver
    recv_msg = await safe_send(client, trade["receiver_id"], recv_text, InlineKeyboardMarkup(recv_buttons))
    if recv_msg:
        trade["recv_chat_id"] = trade["receiver_id"]
        trade["recv_msg_id"] = recv_msg.id
        debug("Sent to receiver DM")
    else:
        recv_msg = await safe_send(client, trade["chat_id"], recv_text, InlineKeyboardMarkup(recv_buttons))
        if recv_msg:
            trade["recv_chat_id"] = trade["chat_id"]
            trade["recv_msg_id"] = recv_msg.id
            debug("Sent to group")
    
    await callback.answer("✅ Waifu selected!")


@Client.on_callback_query(filters.regex(r"^tr_(\d+)_(\d+)$"))
async def receiver_select_cb(client: Client, callback: CallbackQuery):
    """Receiver picks waifu"""
    user = callback.from_user
    parts = callback.data.split("_")
    trade_id = parts[1]
    waifu_idx = int(parts[2])
    
    debug(f"Receiver select: trade={trade_id}, idx={waifu_idx}")
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if trade["receiver_id"] != user.id:
        await callback.answer("❌ Not for you!", show_alert=True)
        return
    
    if trade["status"] != "waiting":
        await callback.answer("❌ Invalid state!", show_alert=True)
        return
    
    receiver_waifus = trade.get("receiver_waifus", [])
    if waifu_idx >= len(receiver_waifus):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = receiver_waifus[waifu_idx]
    trade["receiver_waifu"] = selected
    trade["status"] = "confirm"
    
    debug(f"Receiver selected: {get_waifu_name(selected)} (ID: {get_waifu_id(selected)})")
    
    sender_text = format_waifu_trade(trade["sender_waifu"])
    recv_text = format_waifu_trade(selected)
    
    confirm_text = f"""
💘 **Confirm Trade**

**{trade['sender_name']}** offers:
{sender_text}

**{trade['receiver_name']}** offers:
{recv_text}

⚠️ Both click ✅ to complete!
"""
    
    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
        ]
    ])
    
    # Update all messages
    try:
        await callback.message.edit_text(confirm_text, reply_markup=confirm_buttons)
    except:
        pass
    
    await safe_edit(client, trade["chat_id"], trade["msg_id"], confirm_text, confirm_buttons)
    await safe_send(client, trade["sender_id"], confirm_text, confirm_buttons)
    
    await callback.answer("✅ Now both confirm!")


@Client.on_callback_query(filters.regex(r"^ty_(\d+)$"))
async def confirm_trade_cb(client: Client, callback: CallbackQuery):
    """Confirm trade"""
    user = callback.from_user
    trade_id = callback.data.split("_")[1]
    
    debug(f"Confirm: trade={trade_id}, user={user.id}")
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if user.id not in [trade["sender_id"], trade["receiver_id"]]:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    if trade["status"] != "confirm":
        await callback.answer("❌ Not ready!", show_alert=True)
        return
    
    # Mark confirmed
    if user.id == trade["sender_id"]:
        if trade["sender_ok"]:
            await callback.answer("Already confirmed!")
            return
        trade["sender_ok"] = True
        debug("Sender confirmed")
    else:
        if trade["receiver_ok"]:
            await callback.answer("Already confirmed!")
            return
        trade["receiver_ok"] = True
        debug("Receiver confirmed")
    
    await callback.answer("✅ Confirmed!")
    
    # Both confirmed?
    if trade["sender_ok"] and trade["receiver_ok"]:
        debug("=== EXECUTING TRADE ===")
        
        try:
            sender_id = trade["sender_id"]
            receiver_id = trade["receiver_id"]
            sender_waifu = trade["sender_waifu"]
            receiver_waifu = trade["receiver_waifu"]
            
            sender_wid = get_waifu_id(sender_waifu)
            receiver_wid = get_waifu_id(receiver_waifu)
            sender_img = get_waifu_image(sender_waifu)
            receiver_img = get_waifu_image(receiver_waifu)
            
            debug(f"Sender gives: ID={sender_wid}")
            debug(f"Receiver gives: ID={receiver_wid}")
            
            # Remove with image match
            db.remove_from_collection_by_image(sender_id, sender_wid, sender_img)
            db.remove_from_collection_by_image(receiver_id, receiver_wid, receiver_img)
            
            # Add to new owners
            waifu_for_sender = {
                "id": receiver_wid,
                "waifu_id": receiver_wid,
                "name": get_waifu_name(receiver_waifu),
                "waifu_name": get_waifu_name(receiver_waifu),
                "anime": get_waifu_anime(receiver_waifu),
                "waifu_anime": get_waifu_anime(receiver_waifu),
                "rarity": get_waifu_rarity(receiver_waifu),
                "waifu_rarity": get_waifu_rarity(receiver_waifu),
                "image": receiver_img,
                "waifu_image": receiver_img,
                "obtained_method": "trade"
            }
            
            waifu_for_receiver = {
                "id": sender_wid,
                "waifu_id": sender_wid,
                "name": get_waifu_name(sender_waifu),
                "waifu_name": get_waifu_name(sender_waifu),
                "anime": get_waifu_anime(sender_waifu),
                "waifu_anime": get_waifu_anime(sender_waifu),
                "rarity": get_waifu_rarity(sender_waifu),
                "waifu_rarity": get_waifu_rarity(sender_waifu),
                "image": sender_img,
                "waifu_image": sender_img,
                "obtained_method": "trade"
            }
            
            db.add_to_collection(sender_id, waifu_for_sender)
            db.add_to_collection(receiver_id, waifu_for_receiver)
            
            debug("=== TRADE COMPLETE ===")
            
            # Success message
            sender_w = format_waifu_trade(waifu_for_sender)
            receiver_w = format_waifu_trade(waifu_for_receiver)
            
            success_text = f"""
🎉 **Trade Complete!** 🎉

**{trade['sender_name']}** received:
{sender_w}

**{trade['receiver_name']}** received:
{receiver_w}

💖 Enjoy your new waifus!
"""
            
            try:
                await callback.message.edit_text(success_text)
            except:
                pass
            
            await safe_edit(client, trade["chat_id"], trade["msg_id"], success_text)
            
            if trade.get("recv_msg_id"):
                await safe_edit(client, trade["recv_chat_id"], trade["recv_msg_id"], success_text)
            
            await safe_send(client, trade["sender_id"], success_text)
            await safe_send(client, trade["receiver_id"], success_text)
            
        except Exception as e:
            debug(f"TRADE ERROR: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(f"❌ Trade failed: {e}")
        
        if trade_id in active_trades:
            del active_trades[trade_id]
    
    else:
        s = "✅" if trade["sender_ok"] else "⏳"
        r = "✅" if trade["receiver_ok"] else "⏳"
        
        status_text = f"""
💘 **Trade Confirmation**

**{trade['sender_name']}:** {s}
**{trade['receiver_name']}:** {r}

⏳ Waiting for both...
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
            ]
        ])
        
        try:
            await callback.message.edit_text(status_text, reply_markup=buttons)
        except:
            pass
        
        await safe_edit(client, trade["chat_id"], trade["msg_id"], status_text, buttons)


@Client.on_callback_query(filters.regex(r"^tc_(\d+)$"))
async def cancel_trade_cb(client: Client, callback: CallbackQuery):
    """Cancel trade"""
    user = callback.from_user
    trade_id = callback.data.split("_")[1]
    
    debug(f"Cancel trade: {trade_id}")
    
    if trade_id not in active_trades:
        await callback.answer("❌ Already cancelled!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if user.id not in [trade["sender_id"], trade["receiver_id"]]:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    cancel_text = f"❌ **Trade Cancelled**\n\nCancelled by **{user.first_name}**"
    
    try:
        await callback.message.edit_text(cancel_text)
    except:
        pass
    
    await safe_edit(client, trade["chat_id"], trade["msg_id"], cancel_text)
    
    if trade.get("recv_msg_id"):
        await safe_edit(client, trade["recv_chat_id"], trade["recv_msg_id"], cancel_text)
    
    other_id = trade["receiver_id"] if user.id == trade["sender_id"] else trade["sender_id"]
    await safe_send(client, other_id, cancel_text)
    
    del active_trades[trade_id]
    debug(f"Trade {trade_id} cancelled")
    
    await callback.answer("Cancelled!", show_alert=True)


@Client.on_message(filters.command(["mytrades", "trades"], prefixes=config.COMMAND_PREFIX))
async def mytrades_command(client: Client, message: Message):
    """View pending trades"""
    user = message.from_user
    
    my_trades = []
    for t in active_trades.values():
        if t["sender_id"] == user.id:
            my_trades.append(f"📤 To **{t['receiver_name']}** ({t['status']})")
        elif t["receiver_id"] == user.id:
            my_trades.append(f"📥 From **{t['sender_name']}** ({t['status']})")
    
    if not my_trades:
        await message.reply_text("📭 No pending trades!")
    else:
        await message.reply_text("📋 **Your Trades**\n\n" + "\n".join(my_trades))


@Client.on_message(filters.command(["canceltrade", "ctrade"], prefixes=config.COMMAND_PREFIX))
async def canceltrade_command(client: Client, message: Message):
    """Cancel all your trades"""
    user = message.from_user
    
    count = 0
    for tid in list(active_trades.keys()):
        t = active_trades[tid]
        if t["sender_id"] == user.id or t["receiver_id"] == user.id:
            del active_trades[tid]
            count += 1
    
    if count:
        await message.reply_text(f"✅ Cancelled {count} trade(s)!")
    else:
        await message.reply_text("📭 No trades to cancel.")
