from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from typing import List, Dict
from database import db
from helpers import get_waifu_manager, Utils
import config
import logging

logger = logging.getLogger(__name__)

__MODULE__ = "Collection"
__HELP__ = """
📦 **Collection Commands**

• `/collection` - View your waifu collection
• `/mycollection` - Alias for collection
• `/col` - Short alias for collection
• `/waifu <name>` - View specific waifu details
• `/gift <waifu_id>` (reply) - Gift a waifu to someone

Use the inline buttons to navigate pages and filter by rarity.
"""

ITEMS_PER_PAGE = 5


# ─────────────────────────────────────────────────────────────
#  Helper: unified way to get a user's collection
# ─────────────────────────────────────────────────────────────

def get_user_collection_unified(user_id: int) -> List[Dict]:
    """
    Read the collection from both possible places:
    1) collections table
    2) users.collection (embedded array)
    Prefer the collections table if it has entries.
    """
    # 1) collections table
    table_items = db.get_full_collection(user_id)  # uses db.collections.find(...)
    if table_items:
        logger.info(f"[COL] User {user_id}: {len(table_items)} in collections table")
        return table_items

    # 2) embedded array in users collection
    user = db.get_user(user_id)
    if user and user.get("collection"):
        embedded = user["collection"]
        logger.info(f"[COL] User {user_id}: {len(embedded)} in embedded user.collection")
        return embedded

    logger.info(f"[COL] User {user_id}: collection empty in both locations")
    return []


# ─────────────────────────────────────────────────────────────
#  /collection command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["collection", "mycollection", "col"], prefixes=config.COMMAND_PREFIX))
async def collection_command(client: Client, message: Message):
    user = message.from_user
    await show_collection_message(message, user.id, page=1)


async def show_collection_message(message: Message, user_id: int, page: int = 1):
    wm = get_waifu_manager()

    all_waifus = get_user_collection_unified(user_id)
    total = len(all_waifus)

    if total == 0:
        text = """
📦 **Your Collection**

Your collection is empty!

Use /smash to start collecting waifus!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")]
        ])
        await message.reply_text(text, reply_markup=buttons)
        return

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total)
    page_waifus = all_waifus[start:end]

    text = f"📦 **Your Collection** ({total} waifus)\n"
    text += f"Page {page}/{total_pages}\n\n"

    for w in page_waifus:
        # Support both schemas: table (`waifu_*`) and embedded (`name`, `anime`, etc.)
        name = w.get("waifu_name") or w.get("name") or "Unknown"
        anime = w.get("waifu_anime") or w.get("anime") or "Unknown"
        rarity = w.get("waifu_rarity") or w.get("rarity") or "common"
        power = w.get("waifu_power") or w.get("power") or 0

        rarity_emoji = wm.get_rarity_emoji(rarity)
        text += f"{rarity_emoji} **{name}**\n"
        text += f"   └ {anime} | ⚔️ {power}\n"

    buttons = build_collection_keyboard(page, total_pages)

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────────────────────
#  Callback handlers for pagination & filters
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

    all_waifus = get_user_collection_unified(user_id)
    total = len(all_waifus)

    if total == 0:
        text = """
📦 **Your Collection**

Your collection is empty! 😢

Use /smash to start collecting waifus!
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
        ])
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
        return

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total)
    page_waifus = all_waifus[start:end]

    text = f"📦 **Your Collection** ({total} waifus)\n"
    text += f"Page {page}/{total_pages}\n\n"

    for w in page_waifus:
        name = w.get("waifu_name") or w.get("name") or "Unknown"
        anime = w.get("waifu_anime") or w.get("anime") or "Unknown"
        rarity = w.get("waifu_rarity") or w.get("rarity") or "common"
        power = w.get("waifu_power") or w.get("power") or 0

        rarity_emoji = wm.get_rarity_emoji(rarity)
        text += f"{rarity_emoji} **{name}**\n"
        text += f"   └ {anime} | ⚔️ {power}\n"

    buttons = build_collection_keyboard(page, total_pages)

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer()


def build_collection_keyboard(page: int, total_pages: int):
    buttons = []
    nav_row = []

    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_page_{page-1}"))

    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))

    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_page_{page+1}"))

    buttons.append(nav_row)

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


@Client.on_callback_query(filters.regex(r"^col_filter_(\w+)$"))
async def collection_filter_callback(client: Client, callback: CallbackQuery):
    rarity = callback.data.split("_")[2]
    user = callback.from_user
    wm = get_waifu_manager()

    all_waifus = get_user_collection_unified(user.id)
    if not all_waifus:
        await callback.answer("Your collection is empty!", show_alert=True)
        return

    filtered = []
    for w in all_waifus:
        r = w.get("waifu_rarity") or w.get("rarity") or "common"
        if r.lower() == rarity.lower():
            filtered.append(w)

    if not filtered:
        await callback.answer(f"No {rarity} waifus in your collection!", show_alert=True)
        return

    rarity_emoji = wm.get_rarity_emoji(rarity)
    text = f"{rarity_emoji} **Your {rarity.title()} Waifus** ({len(filtered)})\n\n"

    for w in filtered[:10]:
        name = w.get("waifu_name") or w.get("name") or "Unknown"
        anime = w.get("waifu_anime") or w.get("anime") or "Unknown"
        text += f"• **{name}** - {anime}\n"

    if len(filtered) > 10:
        text += f"\n_...and {len(filtered) - 10} more_"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Collection", callback_data="view_collection")]
    ])

    await callback.message.edit_text(text, reply_markup=buttons)
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^col_info$"))
async def collection_info_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Use arrows to navigate pages!")


# ─────────────────────────────────────────────────────────────
#  /waifu info
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["waifu", "waifuinfo"], prefixes=config.COMMAND_PREFIX))
async def waifu_info_command(client: Client, message: Message):
    wm = get_waifu_manager()
    user = message.from_user

    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/waifu <name>`\n\n"
            "Example: `/waifu Hinata`"
        )
        return

    waifu_name = " ".join(message.command[1:])
    waifu = wm.get_waifu_by_name(waifu_name)

    if not waifu:
        results = wm.search_waifus(waifu_name)
        if results:
            text = f"🔍 **Search Results for '{waifu_name}':**\n\n"
            for w in results[:5]:
                rarity_emoji = wm.get_rarity_emoji(w.get("rarity", "common"))
                text += f"{rarity_emoji} {w.get('name')} - {w.get('anime')}\n"
            await message.reply_text(text)
        else:
            await message.reply_text(f"❌ Waifu '{waifu_name}' not found!")
        return

    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))

    # Check ownership (from both sources)
    all_waifus = get_user_collection_unified(user.id)
    owned = False
    for w in all_waifus:
        wid = w.get("waifu_id") or w.get("id")
        if wid == waifu.get("id"):
            owned = True
            break

    owned_text = "✅ You own this waifu!" if owned else "❌ Not in your collection"

    text = f"""
{rarity_emoji} **{waifu.get('name')}**

📺 **Anime:** {waifu.get('anime')}
💎 **Rarity:** {waifu.get('rarity', 'common').title()}
⚔️ **Power:** {waifu.get('power', 0)}
🆔 **ID:** {waifu.get('id')}

{owned_text}
"""

    image_url = waifu.get("image")
    if image_url:
        try:
            await message.reply_photo(photo=image_url, caption=text)
        except Exception:
            await message.reply_text(text)
    else:
        await message.reply_text(text)


# ─────────────────────────────────────────────────────────────
#  /gift
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command(["gift", "give"], prefixes=config.COMMAND_PREFIX))
async def gift_waifu_command(client: Client, message: Message):
    user = message.from_user

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

    # Check ownership via main collections table (trading uses that)
    waifu = db.get_waifu_from_collection(user.id, waifu_id)
    if not waifu:
        await message.reply_text("❌ You don't own this waifu!")
        return

    # Ensure target exists
    db.get_or_create_user(target_user.id, target_user.username, target_user.first_name)

    # Move from sender to receiver using your DB helpers
    db.remove_from_collection(user.id, waifu_id)
    from helpers import get_waifu_manager
    wm = get_waifu_manager()
    full_waifu = wm.get_waifu_by_id(waifu_id)
    if full_waifu:
        db.add_to_collection(target_user.id, full_waifu)

    waifu_name = waifu.get("waifu_name") or waifu.get("name") or "Unknown"

    await message.reply_text(
        f"🎁 **Gift Successful!**\n\n"
        f"You gifted **{waifu_name}** to "
        f"{Utils.mention_user(target_user.id, target_user.first_name)}!"
    )
