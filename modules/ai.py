import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram import enums
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

from config import OWNER_ID, SUDO_USERS, TG_WAIFU_CHANNEL
from database import db

AIBOORU_API = "https://aibooru.online/posts.json"

SESSIONS = {}  # user_id → session data

def allowed_users():
    if isinstance(SUDO_USERS, (list, tuple, set)):
        return [OWNER_ID, *SUDO_USERS]
    return [OWNER_ID, SUDO_USERS]

# ---------------- HELPERS ----------------

def get_best_image(post):
    # ❌ skip videos / invalid
    if post.get("file_ext") not in ("jpg", "jpeg", "png", "webp"):
        return None

    return (
        post.get("large_file_url")
        or post.get("file_url")
        or post.get("preview_file_url")
    )


async def fetch_posts(tag, before_id=None):
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


    async with aiohttp.ClientSession() as session:
        async with session.get(AIBOORU_API, params=params) as r:
            if r.status != 200:
                return []
            return await r.json()


# minor speed help
async def warm_image(url):
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
            InlineKeyboardButton("⏮️ Page", callback_data="page_prev"),
            InlineKeyboardButton("⏭️ Page", callback_data="page_next")
        ],
        [
            InlineKeyboardButton("⭐️ Rarity", callback_data="set_rarity"),
            InlineKeyboardButton("📤 Upload", callback_data="upload")
        ],
        [
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


# ---------------- COMMAND ----------------

@Client.on_message(filters.command("ai") & filters.user(allowed_users()))
async def ai_search(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /ai <tag>")

    tag = message.text.split(maxsplit=1)[1].strip()
    msg = await message.reply_text("🔍 Searching Aibooru...")

    posts = await fetch_posts(tag)
    if not posts:
        return await msg.edit_text("❌ No results found.")

    img = get_best_image(posts[0])
    if not img:
        return await msg.edit_text("❌ First post has no valid image.")

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
        img,
        caption=f"🏷 `{tag}`",
        reply_markup=nav_buttons(0, len(posts))
    )


# ---------------- CALLBACKS ----------------

@Client.on_callback_query(filters.user(allowed_users()))
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
        return await cb.answer(
            f"Image {index+1}/{len(posts)}"
        )

    # IMAGE NAV
    if cb.data == "img_prev" and index > 0:
        data["index"] -= 1
    elif cb.data == "img_next" and index < len(posts) - 1:
        data["index"] += 1

    # PAGE NEXT (REAL)
    elif cb.data == "page_next":
        last_id = posts[-1]["id"]
        new_posts = await fetch_posts(data["tag"], last_id)

        if not new_posts:
            return await cb.answer("No more pages")

        data["posts"] = new_posts
        data["index"] = 0

    # PAGE PREV (disabled safely)
    elif cb.data == "page_prev":
        return await cb.answer("⬅️ Previous page not supported")

    # RARITY
    elif cb.data == "set_rarity":
        return await cb.message.edit_reply_markup(rarity_buttons())

    elif cb.data.startswith("rar_"):
        data["rarity"] = cb.data.split("_")[1]

        await cb.answer(f"Rarity set: {data['rarity'].title()}")

    # 🔥 bring back main buttons
        return await cb.message.edit_reply_markup(
        nav_buttons(data["index"], len(data["posts"]))
        )

    # UPLOAD
    elif cb.data == "upload":
        data["await"] = "name_anime"
        return await cb.message.reply_text(
            "✍️ Send in ONE message:\n\n"
            "`Name | Anime`\n\n"
            "Example:\n"
            "`Makima | Chainsaw Man`",
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
        return await cb.answer("⚠️ Skip duplicate edit")


# ---------------- TEXT INPUT HANDLER ----------------

@Client.on_message(filters.user(allowed_users()))
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
            "❌ Invalid format.\nUse:\n`Name | Anime`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    name, anime = parts
    post = data["posts"][data["index"]]
    img = get_best_image(post)

    if not img:
        return await message.reply_text("❌ Invalid image")

    caption = (
        f"Name: {name}\n"
        f"Anime: {anime}\n"
        f"Rarity: {data['rarity'].title()}"
    )

    sent = await client.send_photo(
        TG_WAIFU_CHANNEL,
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
