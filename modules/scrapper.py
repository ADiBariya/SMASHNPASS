import re
import os
import json
import shutil
import asyncio
import uuid
import aiohttp
import requests
from PIL import Image
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from config import OWNER_ID, GIT_REPO, GIT_BRANCH, GIT_TOKEN, TG_WAIFU_CHANNEL
from database import db
import time

__MODULE__ = "Scrapper"
__HELP__ = "/search <value> - Search Rule34 autocomplete (Owner Only)"

# Headers for Autocomplete API
AC_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://rule34.xxx",
    "referer": "https://rule34.xxx/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

AC_URL = "https://ac.rule34.xxx/autocomplete.php"

# Headers for Rule34 Search
SEARCH_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "priority": "u=0, i",
    "referer": "https://rule34.xxx/index.php?page=post&s=list&tags=all",
    "sec-ch-ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

SEARCH_COOKIES = {
    "cf_clearance": "VXDk.NeVlLOb9h6TMtHoHxPNPrmJOwRXF4u9pzxb90U-1765293366-1.2.1.1-pgJkppDHUdc8dL18Gmv_e4KsRYFPp61IgkTWfUrMCS2SEWUrl27jhdHerLBuqGpYI0kykr_ETQbxDbJMVYEIhJkD0DQke86sUUpmyGLYp5axE8WpzLQ3.G92OisXQ4fDU3cfXZLZpX_CX9j_S0Q67zud.6Hv5Ut61tCa0f.5EZm5dePiJky4vYBVUJu1o.gXJB1ozWXxGHjjqUtZfXPKevm553YQf3YYaEbwg9oGUBY",
    "gdpr": "1",
    "gdpr-consent": "1"
}

SEARCH_URL = "https://rule34.xxx/index.php"

# Storage
SEARCH_RESULTS = {} # {user_id: [list of tag names]}
PAGINATION_DATA = {} # {
    # user_id: {
    #   "index": 0, 
    #   "items": [{"img": url, "caption": title, "link": full_url}, ...],
    #   "tag": "tag_name",
    #   "pid": 0
    # }
# }

# --- Helpers ---

def format_row(index, type_, name, count):
    if len(name) > 35:
        name = name[:32] + "..."
    return f"{index:<3} {type_:<10} {name:<36} ({count})"

async def scrape_images(tag_name, pid=0):
    params = {
        "page": "post",
        "s": "list",
        "tags": tag_name,
        "pid": pid
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(SEARCH_URL, headers=SEARCH_HEADERS, params=params, cookies=SEARCH_COOKIES) as resp:
            if resp.status != 200:
                raise Exception(f"Status {resp.status}")
            html = await resp.text()

    # Pattern to capture link, src and title
    pattern = re.compile(r'<span[^>]+class="thumb"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]+title="([^"]+)"', re.DOTALL)
    matches = pattern.findall(html)
    
    parsed_items = []
    for href, src, title in matches:
         full_link = f"https://rule34.xxx/{href.lstrip('/')}"
         caption = f"🔗 [Source]({full_link})"
         parsed_items.append({"img": src, "caption": caption, "link": full_link})
         
    return parsed_items

async def download_image(url):
    # Use a unique temporary directory
    temp_id = str(uuid.uuid4())
    download_dir = f"Downloads/{temp_id}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        command = [
            'gallery-dl',
            '--config', 'Cookies/config.json',
            '--directory', download_dir,
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return None

        downloaded_files = os.listdir(download_dir)
        if not downloaded_files:
            return None
            
        filename = downloaded_files[0]
        file_path = os.path.join(download_dir, filename)
        
        # Determine file extension and process image
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            def process_img():
                with Image.open(file_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    max_dim = 2048
                    if img.height > max_dim or img.width > max_dim:
                        img.thumbnail((max_dim, max_dim))
                    img.save(file_path, 'JPEG', quality=95) # Save as same file or new? Overwrite for upload.
            
            # Run blocking image processing in executor
            await asyncio.get_event_loop().run_in_executor(None, process_img)
            
        return file_path, download_dir # Return dir so we can cleanup
        
    except Exception as e:
        print(f"Error downloading: {e}")
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        return None

def upload_to_catbox_sync(file_path):
    url = "https://catbox.moe/user/api.php"
    files = {"fileToUpload": open(file_path, "rb")}
    data = {"reqtype": "fileupload"}
    response = requests.post(url, data=data, files=files)
    return response.text

async def upload_to_catbox(file_path):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, upload_to_catbox_sync, file_path)

def get_anime_info_sync(name):
    url = "https://graphql.anilist.co"
    query = """
    query ($search: String) {
      Character(search: $search) {
        name {
          full
        }
        media(type: ANIME) {
          nodes {
            title {
              romaji
              english
              native
            }
          }
        }
      }
    }
    """
    variables = {"search": name}
    response = requests.post(url, json={"query": query, "variables": variables})
    data = response.json()

    if "errors" in data or not data.get("data", {}).get("Character"):
        return None

    character = data["data"]["Character"]["name"]["full"]
    anime_list = data["data"]["Character"]["media"]["nodes"]
    
    anime_name = "Unknown"
    if anime_list:
        title = anime_list[0]["title"]
        anime_name = title["english"] or title["romaji"] or title["native"]

    return {"character": character, "anime": anime_name}

async def get_anime_info(name):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_anime_info_sync, name)

def update_db(name, anime, rarity, image_url):
    # Generate a simple time-based ID since we aren't using the file anymore
    next_id = int(time.time())
        
    new_entry = {
        "id": next_id,
        "name": name,
        "anime": anime,
        "rarity": rarity,
        "image": image_url
    }
    
    # Sync to MongoDB (Live Update)
    try:
        db.upsert_waifu(new_entry)
        print(f"✅ [DB] Upserted waifu {next_id} to MongoDB")
    except Exception as e:
        print(f"❌ [DB] Failed to upsert to Mongo: {e}")

    return new_entry

# --- Handlers ---

@Client.on_message(filters.command("search") & filters.user([OWNER_ID, 5162885921, 1737646273]))
async def search_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/search <value>`")
    
    query = message.text.split(maxsplit=1)[1]
    msg = await message.reply_text("🔍 Searching...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(AC_URL, headers=AC_HEADERS, params={"q": query}) as response:
                if response.status != 200:
                    return await msg.edit_text(f"❌ Error: API returned {response.status}")
                data = await response.json(content_type=None)
        
        if not data:
            return await msg.edit_text("❌ No results found.")
        
        items = data[:12]
        
        tag_names = []
        rows = []
        header = f"{'#':<3} {'Type':<10} {'Name':<36} {'Count'}"
        separator = "-" * len(header)
        
        for idx, item in enumerate(items, 1):
            label = item.get("label", "")
            type_text = item.get("type", "Unknown").capitalize()
            
            match = re.match(r"^(.*) \((\d+)\)$", label)
            if match:
                name = match.group(1)
                count = match.group(2)
            else:
                name = item.get("value", label)
                count = "?"
            
            tag_names.append(name)
            rows.append(format_row(idx, type_text, name, count))
            
        SEARCH_RESULTS[message.from_user.id] = tag_names
        
        table = "\n".join([header, separator] + rows)
        text = f"**Results for:** `{query}`\n\n```\n{table}\n```"
        
        buttons = []
        num_items = len(items)
        row = []
        for i in range(1, num_items + 1):
            row.append(InlineKeyboardButton(str(i), callback_data=f"qclick_{i}"))
            if len(row) == 4:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
            
        await msg.edit_text(text, parse_mode=enums.ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

@Client.on_callback_query(filters.regex(r"^qclick_(\d+)$"))
async def handle_click(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    idx = int(callback_query.matches[0].group(1)) - 1
    
    if user_id not in SEARCH_RESULTS or idx >= len(SEARCH_RESULTS[user_id]):
        return await callback_query.answer("❌ Session expired or invalid index.", show_alert=True)
    
    tag_name = SEARCH_RESULTS[user_id][idx]
    await callback_query.answer(f"🔍 Searching for: {tag_name}")
    
    try:
        parsed_items = await scrape_images(tag_name, pid=0)
        
        if not parsed_items:
             return await callback_query.message.reply_text("❌ No images found for this tag.")
             
        PAGINATION_DATA[user_id] = {
            "index": 0,
            "items": parsed_items,
            "tag": tag_name,
            "pid": 0
        }
        
        item = parsed_items[0]
        buttons = [
            [
                InlineKeyboardButton("Previous", callback_data="nav_prev"),
                InlineKeyboardButton(f"1/{len(parsed_items)}", callback_data="nav_count"),
                InlineKeyboardButton("Next", callback_data="nav_next")
            ],
            [
                InlineKeyboardButton("Prev Page", callback_data="nav_page_prev"),
                InlineKeyboardButton("Close", callback_data="nav_close"),
                InlineKeyboardButton("Next Page", callback_data="nav_page_next")
            ],
            [
                InlineKeyboardButton("Upload to Channel", callback_data="nav_add_db")
            ]
        ]
        
        await callback_query.message.reply_photo(
            photo=item["img"],
            caption=item["caption"][:1024],
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await callback_query.message.reply_text(f"❌ Error: {str(e)}")

@Client.on_callback_query(filters.regex(r"^nav_(prev|next|count|close|page_prev|page_next|add_db)$"))
async def handle_pagination(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    action = callback_query.matches[0].group(1)

    if action == "close":
        if user_id in PAGINATION_DATA:
            del PAGINATION_DATA[user_id]
        await callback_query.message.delete()
        await callback_query.message.reply_text("🔒 Closed.", quote=False)
        return
    
    if user_id not in PAGINATION_DATA:
        return await callback_query.answer("❌ Session expired.", show_alert=True)
    
    data = PAGINATION_DATA[user_id]
    index = data["index"]
    items = data["items"]
    current_pid = data.get("pid", 0)
    tag_name = data.get("tag", "")

    if action == "add_db":
        # Change buttons to rarity selection
        rarity_buttons = [
            [
                InlineKeyboardButton("Common", callback_data="rarity_common"),
                InlineKeyboardButton("Rare", callback_data="rarity_rare")
            ],
            [
                InlineKeyboardButton("Epic", callback_data="rarity_epic"),
                InlineKeyboardButton("Legendary", callback_data="rarity_legendary")
            ]
        ]
        await callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(rarity_buttons))
        return

    # Handle Page Switching
    if action == "page_prev":
        if current_pid == 0:
            return await callback_query.answer("⚠ You are on the first page of results.", show_alert=True)
        
        new_pid = max(0, current_pid - 42)
        try:
            await callback_query.answer(f"Loading previous page... (PID: {new_pid})")
            new_items = await scrape_images(tag_name, new_pid)
            if not new_items:
                return await callback_query.answer("⚠ Previous page is empty?", show_alert=True)
                
            PAGINATION_DATA[user_id]["items"] = new_items
            PAGINATION_DATA[user_id]["index"] = 0
            PAGINATION_DATA[user_id]["pid"] = new_pid
            items = new_items
            new_index = 0
            
        except Exception as e:
            return await callback_query.answer(f"❌ Error loading page: {str(e)}", show_alert=True)
            
    elif action == "page_next":
        new_pid = current_pid + 42
        try:
            await callback_query.answer(f"Loading next page... (PID: {new_pid})")
            new_items = await scrape_images(tag_name, new_pid)
            if not new_items:
                return await callback_query.answer("⚠ No more results on next page.", show_alert=True)
                
            PAGINATION_DATA[user_id]["items"] = new_items
            PAGINATION_DATA[user_id]["index"] = 0
            PAGINATION_DATA[user_id]["pid"] = new_pid
            items = new_items
            new_index = 0
            
        except Exception as e:
            return await callback_query.answer(f"❌ Error loading page: {str(e)}", show_alert=True)

    # Handle Image Navigation
    elif action == "count":
        return await callback_query.answer(f"Page {current_pid//42 + 1} | Image {index + 1} of {len(items)}")
    
    elif action == "prev":
        if index == 0:
            return await callback_query.answer("⚠ Start of this result page.", show_alert=True)
        new_index = index - 1
        
    elif action == "next":
        if index == len(items) - 1:
            return await callback_query.answer("⚠ End of this result page. Try 'Next Page'.", show_alert=True)
        new_index = index + 1
    
    else:
        if action in ["page_prev", "page_next"]:
            new_index = 0
        else:
             return
        
    PAGINATION_DATA[user_id]["index"] = new_index
    item = items[new_index]
    
    buttons = [
        [
            InlineKeyboardButton("Previous", callback_data="nav_prev"),
            InlineKeyboardButton(f"{new_index + 1}/{len(items)}", callback_data="nav_count"),
            InlineKeyboardButton("Next", callback_data="nav_next")
        ],
        [
            InlineKeyboardButton("Prev Page", callback_data="nav_page_prev"),
            InlineKeyboardButton("Close", callback_data="nav_close"),
            InlineKeyboardButton("Next Page", callback_data="nav_page_next")
        ],
        [
            InlineKeyboardButton("Upload to Channel", callback_data="nav_add_db")
        ]
    ]
    
    try:
        await callback_query.message.edit_media(
            media=InputMediaPhoto(
                media=item["img"],
                caption=item["caption"][:1024]
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await callback_query.answer(f"❌ Failed to load image: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r"^rarity_(common|rare|epic|legendary)$"))
async def handle_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    rarity = callback_query.matches[0].group(1)
    
    if user_id not in PAGINATION_DATA:
        return await callback_query.answer("❌ Session expired", show_alert=True)
        
    data = PAGINATION_DATA[user_id]
    item = data["items"][data["index"]]
    tag_name = data["tag"]
    source_url = item["link"]
    
    await callback_query.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback_query.message.reply_text(f"⏳ Processing...\nDownloading from: `{source_url}`")
    
    try:
        # 1. Download Image
        result = await download_image(source_url)
        if not result:
            return await status_msg.edit_text("❌ Failed to download media.")
        
        file_path, temp_dir = result
        
        # 2. Upload to Catbox
    try:
        # 1. Download Image
        result = await download_image(source_url)
        if not result:
            return await status_msg.edit_text("❌ Failed to download media.")
        
        file_path, temp_dir = result
        
        try:
            # 2. Clean Name & Get Anime Info
            await status_msg.edit_text(f"⏳ Fetching info for `{tag_name}`...")
            
            clean_name = re.sub(r'\(.*?\)', '', tag_name).replace('_', ' ').strip()
            
            anime_info = await get_anime_info(clean_name)
            
            if anime_info:
                final_name = anime_info["character"]
                final_anime = anime_info["anime"]
            else:
                final_name = clean_name.title()
                final_anime = "Unknown"

            # 3. Send to Channel
            await status_msg.edit_text("⏳ Uploading to Channel...")
            caption = (
                f"Name: {final_name}\n"
                f"Anime: {final_anime}\n"
                f"Rarity: {rarity.capitalize()}"
            )
            
            try:
                sent_msg = await client.send_photo(
                    chat_id=TG_WAIFU_CHANNEL,
                    photo=file_path,
                    caption=caption
                )
                
                image_link = None
                if sent_msg and sent_msg.id:
                    # Construct link manually if needed or use .link if available
                    # For private channels -100..., remove -100 and use /c/
                    req_chat_id = str(TG_WAIFU_CHANNEL)
                    if req_chat_id.startswith("-100"):
                         chat_code = req_chat_id[4:]
                         image_link = f"https://t.me/c/{chat_code}/{sent_msg.id}"
                    else:
                         image_link = sent_msg.link

                if not image_link:
                    image_link = "https://t.me/unknown_link"

                # 4. Update Database (Live Mongo only) - ONLY ON SUCCESS
                new_entry = update_db(final_name, final_anime, rarity, image_link)
            
                await status_msg.edit_text(
                    f"✅ **Processed!**\n\n"
                    f"🆔 ID: `{new_entry['id']}`\n"
                    f"👤 Name: `{final_name}`\n"
                    f"📺 Anime: `{final_anime}`\n"
                    f"✨ Rarity: `{rarity.capitalize()}`\n\n"
                    f"✅ Posted to Channel!"
                )

            except Exception as ch_e:
                 await status_msg.edit_text(f"❌ Failed to post to channel: {ch_e}")
                 # Do not update DB, do not proceed

        finally:
            shutil.rmtree(temp_dir)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Critical Error: {str(e)}")
