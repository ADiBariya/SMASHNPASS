# modules/ai.py - 🖼️ Aibooru AI Scraper Module (Professional Edition)

import aiohttp
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

import config
from database import db


__MODULE__ = "AI Scraper"
__HELP__ = """
🖼️ **AI Image Scraper**

┃ /ai <tag> - Search images from Aibooru
┃ Inline controls for navigation
┃ Upload images directly to waifu channel
"""

AIBOORU_API = "https://aibooru.online/posts.json"

SESSIONS = {}

DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"🖼️ [AI] {msg}")

def get_allowed_users():
    users = [config.OWNER_ID]
    if config.SUDO_USERS:
        if isinstance(config.SUDO_USERS, (list, tuple, set)):
            users.extend(config.SUDO_USERS)
        else:
            users.append(config.SUDO_USERS)
    return list(set(users))

ALLOWED_USERS = get_allowed_users()

def is_allowed(_, __, update):
    return update.from_user and update.from_user.id in ALLOWED_USERS

allowed_filter = filters.create(is_allowed)


def get_best_image(post):
    """Return best usable image url"""
    if post.get("file_ext") not in ("jpg", "jpeg", "png", "webp"):
        return None
    return (
        post.get("large_file_url")
        or post.get("file_url")
        or post.get("preview_file_url")
    )


async def fetch_posts(tag, before_id=None):
    """Fetch posts using real Aibooru pagination"""
    if before_id:
        tag = f"{tag} id:<{before_id}"

    params = {
        "tags": tag,
        "limit": 20
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(AIBOORU_API, params=params) as r:
            if r.status != 200:
                return []
            return await r.json()


async def warm_image(url):
    """Minor speed-up by warming next image"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=5):
                pass
    except:
        pass


def nav_buttons(index, total):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Img", callback_data="img_prev"),
            InlineKeyboardButton(f"{index+1}/{total}", callback_data="info"),
            InlineKeyboardButton("➡️ Img", callback_data="img_next")
        ],
        [
            InlineKeyboardButton("⏭️ Next Page", callback_data="page_next"),
            InlineKeyboardButton("⭐️ Rarity", callback_data="set_rarity")
        ],
        [
            InlineKeyboardButton("📤 Upload", callback_data="upload"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])


def rarity_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Common", callback_data="rar_common"),
            InlineKeyboardButton("Rare", callback_data="rar_rare")
        ],
        [
            InlineKeyboardButton("Epic", callback_data="rar_epic"),
            InlineKeyboardButton("Legendary", callback_data="rar_legendary")
        ]
    ])


@Client.on_message(filters.command("ai", config.COMMAND_PREFIX) & allowed_filter)
async def ai_search(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /ai <tag>")

    tag = message.text.split(maxsplit=1)[1].strip()
    debug(f"Search started: {tag}")

    msg = await message.reply_text("🔍 Searching Aibooru...")

    posts = await fetch_posts(tag)
    if not posts:
        return await msg.edit_text("❌ No results found.")

    img = get_best_image(posts[0])
    if not img:
        return await msg.edit_text("❌ Invalid first image.")

    SESSIONS[message.from_user.id] = {
        "tag": tag,
        "index": 0,
        "posts": posts,
        "rarity": "common"
    }

    if len(posts) > 1:
        asyncio.create_task(warm_image(get_best_image(posts[1])))

    await msg.delete()
    await message.reply_photo(
        photo=img,
        caption=f"🏷 `{tag}`",
        reply_markup=nav_buttons(0, len(posts))
    )

@Client.on_callback_query(allowed_filter)
async def ai_callbacks(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in SESSIONS:
        return await cb.answer("Session expired", show_alert=True)

    data = SESSIONS[uid]
    posts = data["posts"]
    index = data["index"]

    # CLOSE
    if cb.data == "close":
        del SESSIONS[uid]
        return await cb.message.delete()

    # INFO
    if cb.data == "info":
        return await cb.answer(f"Image {index+1}/{len(posts)}")

    # IMAGE NAV
    if cb.data == "img_prev" and index > 0:
        data["index"] -= 1
    elif cb.data == "img_next" and index < len(posts) - 1:
        data["index"] += 1

    # NEXT PAGE (REAL PAGINATION)
    elif cb.data == "page_next":
        last_id = posts[-1]["id"]
        new_posts = await fetch_posts(data["tag"], last_id)
        if not new_posts:
            return await cb.answer("No more pages")
        data["posts"] = new_posts
        data["index"] = 0

    # RARITY
    elif cb.data == "set_rarity":
        return await cb.message.edit_reply_markup(rarity_buttons())

    elif cb.data.startswith("rar_"):
        data["rarity"] = cb.data.split("_")[1]
        await cb.answer(f"Rarity set: {data['rarity'].title()}")
        return await cb.message.edit_reply_markup(
            nav_buttons(data["index"], len(data["posts"]))
        )

    # UPLOAD
    elif cb.data == "upload":
        data["await"] = "name_anime"
        return await cb.message.reply_text(
            "✍️ Send in ONE message:\n\n`Name | Anime`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    # UPDATE IMAGE
    post = data["posts"][data["index"]]
    img = get_best_image(post)
    if not img:
        return await cb.answer("⚠️ Invalid media skipped")

    nxt = data["index"] + 1
    if nxt < len(posts):
        asyncio.create_task(warm_image(get_best_image(posts[nxt])))

    try:
        await cb.message.edit_media(
            InputMediaPhoto(
                media=img,
                caption=f"🏷 `{data['tag']}`"
            ),
            reply_markup=nav_buttons(data["index"], len(posts))
        )
    except:
        await cb.answer("⚠️ Duplicate edit skipped")

@Client.on_message(allowed_filter & filters.text & ~filters.command(["ai"]))
async def name_anime_handler(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in SESSIONS:
        return

    data = SESSIONS[uid]
    if data.get("await") != "name_anime":
        return

    data.pop("await")

    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) != 2:
        return await message.reply_text(
            "❌ Invalid format.\nUse: `Name | Anime`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    name, anime = parts
    post = data["posts"][data["index"]]
    img = get_best_image(post)

    caption = (
        f"Name: {name}\n"
        f"Anime: {anime}\n"
        f"Rarity: {data['rarity'].title()}"
    )

    sent = await client.send_photo(
        config.TG_WAIFU_CHANNEL,
        img,
        caption=caption
    )

    db.upsert_waifu({
        "name": name,
        "anime": anime,
        "rarity": data["rarity"],
        "image": sent.link
    })

    del SESSIONS[uid]
    await message.reply_text("✅ Uploaded & saved successfully!")
