# modules/marry.py - Waifu Marriage System (FIXED)

import random
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.errors import MessageNotModified
from database import db
import config

MARRY_PAGE_SIZE = 6
MARRY_DEFAULT_IMAGE = "https://files.catbox.moe/nelv7i.jpg"

__MODULE__ = "𝐌𝐚𝐫𝐫𝐲"
__HELP__ = """
💒 **Marriage Commands**

• `/marry` - Propose to a waifu from your collection
• `/mywife` - View your current married waifu
• `/divorce` - Divorce your current waifu
• `/marriages` - View marriage stats

⚠️ **Warning:** If your proposal is rejected, you LOSE that waifu from your collection!

💡 **Tips:**
• Higher rarity = Lower acceptance chance
• You can only marry once every 24 hours
• Divorced waifus stay in your collection
"""

MARRY_COOLDOWN = 24 * 60 * 60  # 24 hours

ACCEPTANCE_CHANCE = {
    "common": 80,
    "rare": 60,
    "epic": 40,
    "legendary": 20
}

# Store active proposals {user_id: proposal_data}
active_proposals = {}

# HELPER FUNCTIONS

def get_safe_image(waifu: dict) -> str:
    """Get valid image URL or file_id from waifu"""
    img = (
        waifu.get("waifu_image")
        or waifu.get("image")
        or waifu.get("file_id")
        or ""
    )
    
    if not img:
        return MARRY_DEFAULT_IMAGE
    
    # Telegram file_id
    if img.startswith(("AgAC", "BAAC", "CAA", "BAA")):
        return img
    
    # HTTP URL
    if img.startswith(("http://", "https://")):
        return img
    
    return MARRY_DEFAULT_IMAGE


def get_rarity_emoji(rarity: str) -> str:
    return {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(rarity).lower(), "⚪")


def get_waifu_id(waifu: dict) -> int:
    wid = waifu.get("waifu_id") or waifu.get("id") or waifu.get("_id") or 0
    try:
        return int(wid)
    except:
        return 0


def get_waifu_name(waifu: dict) -> str:
    return waifu.get("waifu_name") or waifu.get("name") or "Unknown"


def get_waifu_anime(waifu: dict) -> str:
    return waifu.get("waifu_anime") or waifu.get("anime") or "Unknown"


def get_waifu_rarity(waifu: dict) -> str:
    return str(waifu.get("waifu_rarity") or waifu.get("rarity") or "common").lower()


def get_waifu_image(waifu: dict) -> str:
    return waifu.get("waifu_image") or waifu.get("image") or waifu.get("file_id") or ""


def format_time_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "Ready!"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    return f"{seconds}s"


def get_unique_waifus(collection: list) -> list:
    seen = set()
    unique = []
    for w in collection:
        wid = get_waifu_id(w)
        if wid and wid not in seen:
            seen.add(wid)
            unique.append(w)
    return unique


def filter_waifus_by_rarity(waifus: list, rarity: str = None) -> list:
    if not rarity:
        return waifus
    return [w for w in waifus if get_waifu_rarity(w) == rarity]


def paginate(items: list, page: int, size: int):
    start = page * size
    end = start + size
    return items[start:end], len(items)


def extract_target_user(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    if message.entities:
        for ent in message.entities:
            if ent.type.name == "TEXT_MENTION":
                return ent.user
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return None



#  KEYBOARD BUILDER


def build_marry_keyboard(user_id: int, waifus: list, page: int, rarity_filter: str = None):
    """Build keyboard for marry selection"""
    filtered = filter_waifus_by_rarity(waifus, rarity_filter)
    page_items, total = paginate(filtered, page, MARRY_PAGE_SIZE)
    
    buttons = []
    row = []
    
    for w in page_items:
        try:
            real_index = waifus.index(w)
        except ValueError:
            continue
        
        name = get_waifu_name(w)[:15]
        emoji = get_rarity_emoji(get_waifu_rarity(w))
        
        row.append(
            InlineKeyboardButton(
                f"{emoji} {name}",
                callback_data=f"msel_{user_id}_{real_index}"
            )
        )
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Rarity filter row
    buttons.append([
        InlineKeyboardButton("⚪", callback_data=f"mflt_{user_id}_common"),
        InlineKeyboardButton("🔵", callback_data=f"mflt_{user_id}_rare"),
        InlineKeyboardButton("🟣", callback_data=f"mflt_{user_id}_epic"),
        InlineKeyboardButton("🟡", callback_data=f"mflt_{user_id}_legendary"),
        InlineKeyboardButton("♻️", callback_data=f"mflt_{user_id}_all"),
    ])
    
    # Pagination
    nav = []
    total_pages = (total + MARRY_PAGE_SIZE - 1) // MARRY_PAGE_SIZE if total > 0 else 1
    
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"mpg_{user_id}_{page - 1}"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"mpg_{user_id}_{page + 1}"))
    
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"mcan_{user_id}")])
    
    return InlineKeyboardMarkup(buttons)



#  RENDER MARRY PAGE (WITH IMAGE)


async def render_marry_page(client, message, user_id, send_new=False):
    """Render the marry selection page with image"""
    if user_id not in active_proposals:
        try:
            await message.edit_text("❌ Proposal expired! Use /marry again.")
        except:
            pass
        return
    
    proposal = active_proposals[user_id]
    waifus = proposal.get("waifus", [])
    page = proposal.get("page", 0)
    rarity = proposal.get("rarity")
    
    keyboard = build_marry_keyboard(user_id, waifus, page, rarity)
    
    filtered = filter_waifus_by_rarity(waifus, rarity)
    total_pages = (len(filtered) + MARRY_PAGE_SIZE - 1) // MARRY_PAGE_SIZE if filtered else 1
    current_filter = f"🔍 Filter: {rarity.title()}" if rarity else "🔍 Filter: All"
    
    if not filtered:
        text = (
            "💒 **Marriage Proposal**\n\n"
            "❌ No waifus found with this rarity!\n\n"
            "Use ♻️ to reset filter."
        )
    else:
        text = (
            "💒 **Marriage Proposal**\n\n"
            "Choose a waifu from your collection to propose to!\n\n"
            "⚠️ If rejected, you will **LOSE** her forever.\n\n"
            f"{current_filter} | Page {page + 1}/{total_pages}\n\n"
            "Select your waifu:"
        )
    
    try:
        if send_new:
            # Send new message with image
            await message.reply_photo(
                photo=MARRY_DEFAULT_IMAGE,
                caption=text,
                reply_markup=keyboard
            )
        elif message.photo:
            await message.edit_caption(caption=text, reply_markup=keyboard)
        else:
            await message.edit_text(text, reply_markup=keyboard)
    except MessageNotModified:
        pass
    except Exception as e:
        print(f"Error rendering marry page: {e}")



# MARRY COMMAND


@Client.on_message(filters.command(["marry", "propose"], config.COMMAND_PREFIX))
async def marry_command(client: Client, message: Message):
    """Start marriage proposal process"""
    user = message.from_user
    
    # Check active proposal
    if user.id in active_proposals:
        await message.reply_text(
            "❌ **You already have an active proposal!**\n"
            "Complete or cancel it first."
        )
        return
    
    # Check if already married
    marriage = db.get_user_marriage(user.id)
    if marriage and marriage.get("married_to"):
        waifu_name = marriage.get("waifu_name", "your waifu")
        await message.reply_text(
            f"💒 **You're already married to {waifu_name}!**\n\n"
            f"Use `/divorce` first if you want to marry someone else.\n"
            f"Use `/mywife` to see your wife."
        )
        return
    
    # Check cooldown
    last_marry = db.get_user_data(user.id, "last_marry_attempt")
    if last_marry:
        try:
            last_time = datetime.fromisoformat(last_marry)
            elapsed = (datetime.now() - last_time).total_seconds()
            remaining = MARRY_COOLDOWN - elapsed
            
            if remaining > 0:
                await message.reply_text(
                    f"⏳ **Marriage Cooldown!**\n\n"
                    f"You can propose again in **{format_time_remaining(int(remaining))}**\n\n"
                    f"💡 You can only propose once every 24 hours!"
                )
                return
        except Exception as e:
            print(f"Error parsing cooldown: {e}")
    
    # Get collection
    collection = db.get_full_collection(user.id)
    
    if not collection:
        await message.reply_text(
            "❌ **Your collection is empty!**\n\n"
            "Use `/smash` to collect some waifus first! 💕"
        )
        return
    
    unique_waifus = get_unique_waifus(collection)
    
    if not unique_waifus:
        await message.reply_text("❌ No valid waifus in your collection!")
        return
    
    # Store proposal
    active_proposals[user.id] = {
        "waifus": unique_waifus,
        "stage": "selecting",
        "page": 0,
        "rarity": None
    }
    
    keyboard = build_marry_keyboard(user.id, unique_waifus, 0, None)
    
    text = """
💒 **Marriage Proposal**

Choose a waifu from your collection to propose to!

⚠️ **WARNING:** 
If she **rejects** your proposal, you will **LOSE** her from your collection forever!

Select your waifu:
"""
    
    # Send with image
    try:
        await message.reply_photo(
            photo=MARRY_DEFAULT_IMAGE,
            caption=text,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error sending marry image: {e}")
        # Fallback to text
        await message.reply_text(text, reply_markup=keyboard)



# PAGINATION CALLBACK


@Client.on_callback_query(filters.regex(r"^mpg_(\d+)_(\d+)$"))
async def marry_page_callback(client: Client, callback: CallbackQuery):
    """Handle page navigation"""
    try:
        parts = callback.data.split("_")
        uid = int(parts[1])
        page = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != uid:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if uid not in active_proposals:
        await callback.answer("❌ Proposal expired! Use /marry again", show_alert=True)
        return
    
    active_proposals[uid]["page"] = page
    await render_marry_page(client, callback.message, uid)
    await callback.answer()


# FILTER CALLBACK


@Client.on_callback_query(filters.regex(r"^mflt_(\d+)_(\w+)$"))
async def marry_filter_callback(client: Client, callback: CallbackQuery):
    """Handle rarity filter"""
    try:
        parts = callback.data.split("_")
        uid = int(parts[1])
        rarity = parts[2]
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != uid:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if uid not in active_proposals:
        await callback.answer("❌ Proposal expired! Use /marry again", show_alert=True)
        return
    
    active_proposals[uid]["rarity"] = None if rarity == "all" else rarity
    active_proposals[uid]["page"] = 0
    
    await render_marry_page(client, callback.message, uid)
    await callback.answer(f"Filter: {rarity.title()}" if rarity != "all" else "Filter removed")


#  WAIFU SELECTION CALLBACK


@Client.on_callback_query(filters.regex(r"^msel_(\d+)_(\d+)$"))
async def marry_select_callback(client: Client, callback: CallbackQuery):
    """Handle waifu selection"""
    try:
        parts = callback.data.split("_")
        owner_id = int(parts[1])
        waifu_index = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if owner_id not in active_proposals:
        await callback.answer("❌ Proposal expired! Use /marry again", show_alert=True)
        return
    
    proposal = active_proposals[owner_id]
    waifus = proposal.get("waifus", [])
    
    if waifu_index >= len(waifus):
        await callback.answer("❌ Invalid selection!", show_alert=True)
        return
    
    waifu = waifus[waifu_index]
    proposal["selected_waifu"] = waifu
    proposal["stage"] = "confirming"
    
    name = get_waifu_name(waifu)
    anime = get_waifu_anime(waifu)
    rarity = get_waifu_rarity(waifu)
    emoji = get_rarity_emoji(rarity)
    chance = ACCEPTANCE_CHANCE.get(rarity, 50)
    image = get_safe_image(waifu)
    
    text = f"""
💍 **Confirm Proposal**

You want to propose to:

{emoji} **{name}**
📺 Anime: {anime}
💎 Rarity: {rarity.title()}
💕 Acceptance Chance: **{chance}%**

⚠️ **If rejected, you will LOSE this waifu!**

Are you sure?
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💍 Yes, Propose!", callback_data=f"mconf_{owner_id}"),
            InlineKeyboardButton("🔙 Back", callback_data=f"mback_{owner_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"mcan_{owner_id}")]
    ])
    
    try:
        if callback.message.photo:
            # Edit existing photo with new image
            await callback.message.delete()
            await callback.message.reply_photo(
                photo=image,
                caption=text,
                reply_markup=buttons
            )
        else:
            await callback.message.delete()
            await callback.message.reply_photo(
                photo=image,
                caption=text,
                reply_markup=buttons
            )
    except Exception as e:
        print(f"Error in marry_select: {e}")
        try:
            await callback.message.edit_text(text, reply_markup=buttons)
        except:
            await callback.message.reply_text(text, reply_markup=buttons)
    
    await callback.answer()



#  BACK CALLBACK (Return to selection)


@Client.on_callback_query(filters.regex(r"^mback_(\d+)$"))
async def marry_back_callback(client: Client, callback: CallbackQuery):
    """Go back to waifu selection"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if owner_id not in active_proposals:
        await callback.answer("❌ Proposal expired! Use /marry again", show_alert=True)
        return
    
    proposal = active_proposals[owner_id]
    proposal["stage"] = "selecting"
    proposal["selected_waifu"] = None
    
    waifus = proposal.get("waifus", [])
    page = proposal.get("page", 0)
    rarity = proposal.get("rarity")
    
    keyboard = build_marry_keyboard(owner_id, waifus, page, rarity)
    
    filtered = filter_waifus_by_rarity(waifus, rarity)
    total_pages = (len(filtered) + MARRY_PAGE_SIZE - 1) // MARRY_PAGE_SIZE if filtered else 1
    current_filter = f"🔍 Filter: {rarity.title()}" if rarity else "🔍 Filter: All"
    
    text = (
        "💒 **Marriage Proposal**\n\n"
        "Choose a waifu from your collection to propose to!\n\n"
        "⚠️ If rejected, you will **LOSE** her forever.\n\n"
        f"{current_filter} | Page {page + 1}/{total_pages}\n\n"
        "👇 Select your waifu:"
    )
    
    try:
        await callback.message.delete()
        await callback.message.reply_photo(
            photo=MARRY_DEFAULT_IMAGE,
            caption=text,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error going back: {e}")
        await callback.message.reply_text(text, reply_markup=keyboard)
    
    await callback.answer()



# CONFIRM PROPOSAL CALLBACK


@Client.on_callback_query(filters.regex(r"^mconf_(\d+)$"))
async def marry_confirm_callback(client: Client, callback: CallbackQuery):
    """Handle marriage proposal confirmation"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if owner_id not in active_proposals:
        await callback.answer("❌ Proposal expired!", show_alert=True)
        return
    
    proposal = active_proposals[owner_id]
    waifu = proposal.get("selected_waifu")
    
    if not waifu:
        await callback.answer("❌ No waifu selected!", show_alert=True)
        if owner_id in active_proposals:
            del active_proposals[owner_id]
        return
    
    await callback.answer("💍 Proposing...")
    
    name = get_waifu_name(waifu)
    image = get_safe_image(waifu)
    
    proposing_text = f"""
💍 **Proposing to {name}...**

💭 Getting down on one knee...
💐 Presenting flowers...
💕 Waiting for her answer...
"""
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=proposing_text, reply_markup=None)
        else:
            await callback.message.edit_text(proposing_text, reply_markup=None)
    except:
        pass
    
    await asyncio.sleep(2)
    
    # Calculate result
    rarity = get_waifu_rarity(waifu)
    chance = ACCEPTANCE_CHANCE.get(rarity, 50)
    is_accepted = random.randint(1, 100) <= chance
    
    # Set cooldown
    db.set_user_data(owner_id, "last_marry_attempt", datetime.now().isoformat())
    
    # Clean up proposal
    if owner_id in active_proposals:
        del active_proposals[owner_id]
    
    anime = get_waifu_anime(waifu)
    emoji = get_rarity_emoji(rarity)
    waifu_id = get_waifu_id(waifu)
    
    # Update stats
    try:
        stats = db.get_user_marriage_stats(owner_id) or {}
        stats["total_proposals"] = stats.get("total_proposals", 0) + 1
    except:
        stats = {"total_proposals": 1}
    
    if is_accepted:
        # ✅ ACCEPTED
        db.set_user_marriage(owner_id, {
            "married_to": waifu_id,
            "waifu_name": name,
            "waifu_anime": anime,
            "waifu_rarity": rarity,
            "waifu_image": image,
            "married_at": datetime.now().isoformat()
        })
        
        stats["accepted"] = stats.get("accepted", 0) + 1
        
        accept_messages = [
            f"**{name}** blushes and says... \"Yes! I'll marry you!\" 💕",
            f"**{name}** jumps into your arms! \"Of course, baka!\" 💋",
            f"**{name}** tears up with joy... \"I've been waiting for this!\" 😭💕",
            f"**{name}** smiles brightly... \"Forever and always!\" 💒✨",
        ]
        
        text = f"""
🎊 **SHE SAID YES!** 🎊

{random.choice(accept_messages)}

━━━━━━━━━━━━━━━━━━━
{emoji} **{name}**
📺 {anime}
💎 {rarity.title()}
━━━━━━━━━━━━━━━━━━━

💒 You are now married!
Use `/mywife` to see your wife!
"""
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💕 View My Wife", callback_data=f"vwife_{owner_id}")]
        ])
        
    else:
        # ❌ REJECTED
        db.remove_waifu_from_collection(owner_id, waifu_id)
        
        stats["rejected"] = stats.get("rejected", 0) + 1
        
        reject_messages = [
            f"**{name}** looks away... \"I'm sorry, I can't...\" 💔",
            f"**{name}** shakes her head... \"We're better as friends...\" 😢",
            f"**{name}** runs away crying... \"I need time alone!\" 💨",
            f"**{name}** whispers... \"My heart belongs to another...\" 💔",
        ]
        
        text = f"""
💔 **REJECTED...** 💔

{random.choice(reject_messages)}

━━━━━━━━━━━━━━━━━━━
{emoji} **{name}**
📺 {anime}
💎 {rarity.title()}
━━━━━━━━━━━━━━━━━━━

😢 **{name}** has left your collection forever...

💡 Better luck next time!
You can try again in 24 hours.
"""
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Hunt More Waifus", callback_data="play_smash")]
        ])
    
    # Save stats
    try:
        db.set_user_marriage_stats(owner_id, stats)
    except:
        pass
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except:
        await callback.message.reply_text(text, reply_markup=buttons)



# CANCEL PROPOSAL CALLBACK


@Client.on_callback_query(filters.regex(r"^mcan_(\d+)$"))
async def marry_cancel_callback(client: Client, callback: CallbackQuery):
    """Cancel marriage proposal"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your proposal!", show_alert=True)
        return
    
    if owner_id in active_proposals:
        del active_proposals[owner_id]
    
    await callback.answer("❌ Proposal cancelled!")
    
    try:
        await callback.message.delete()
    except:
        try:
            await callback.message.edit_text("❌ **Proposal Cancelled**")
        except:
            pass



#  MY WIFE COMMAND


@Client.on_message(filters.command(["mywife", "wife", "married"], config.COMMAND_PREFIX))
async def mywife_command(client: Client, message: Message):
    """View your married waifu"""
    user = message.from_user
    
    marriage = db.get_user_marriage(user.id)
    
    if not marriage or not marriage.get("married_to"):
        await message.reply_text(
            "💔 **You're not married!**\n\n"
            "Use `/marry` to propose to a waifu from your collection!"
        )
        return
    
    name = marriage.get("waifu_name", "Unknown")
    anime = marriage.get("waifu_anime", "Unknown")
    rarity = marriage.get("waifu_rarity", "common")
    image = marriage.get("waifu_image") or MARRY_DEFAULT_IMAGE
    married_at = marriage.get("married_at", "")
    
    emoji = get_rarity_emoji(rarity)
    
    # Calculate duration
    duration = "Unknown"
    if married_at:
        try:
            married_date = datetime.fromisoformat(married_at)
            days = (datetime.now() - married_date).days
            if days == 0:
                duration = "Today! 💕"
            elif days == 1:
                duration = "1 day"
            else:
                duration = f"{days} days"
        except:
            pass
    
    text = f"""
💒 **Your Wife**

{emoji} **{name}**
━━━━━━━━━━━━━━━━━━━
📺 **Anime:** {anime}
💎 **Rarity:** {rarity.title()}
💕 **Married for:** {duration}

She loves you! 💋
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💔 Divorce", callback_data=f"divcon_{user.id}")]
    ])
    
    try:
        await message.reply_photo(photo=image, caption=text, reply_markup=buttons)
    except Exception as e:
        print(f"Error sending wife image: {e}")
        await message.reply_text(text, reply_markup=buttons)



# VIEW WIFE CALLBACK


@Client.on_callback_query(filters.regex(r"^vwife_(\d+)$"))
async def view_wife_callback(client: Client, callback: CallbackQuery):
    """View wife from callback"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your wife!", show_alert=True)
        return
    
    marriage = db.get_user_marriage(owner_id)
    
    if not marriage or not marriage.get("married_to"):
        await callback.answer("💔 You're not married!", show_alert=True)
        return
    
    name = marriage.get("waifu_name", "Unknown")
    anime = marriage.get("waifu_anime", "Unknown")
    rarity = marriage.get("waifu_rarity", "common")
    image = marriage.get("waifu_image") or MARRY_DEFAULT_IMAGE
    married_at = marriage.get("married_at", "")
    
    emoji = get_rarity_emoji(rarity)
    
    duration = "Unknown"
    if married_at:
        try:
            married_date = datetime.fromisoformat(married_at)
            days = (datetime.now() - married_date).days
            if days == 0:
                duration = "Today! 💕"
            elif days == 1:
                duration = "1 day"
            else:
                duration = f"{days} days"
        except:
            pass
    
    text = f"""
💒 **Your Wife**

{emoji} **{name}**
━━━━━━━━━━━━━━━━━━━
📺 **Anime:** {anime}
💎 **Rarity:** {rarity.title()}
💕 **Married for:** {duration}

She loves you! 💋
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💔 Divorce", callback_data=f"divcon_{owner_id}")]
    ])
    
    try:
        await callback.message.delete()
        await callback.message.reply_photo(photo=image, caption=text, reply_markup=buttons)
    except Exception as e:
        print(f"Error viewing wife: {e}")
        await callback.message.reply_text(text, reply_markup=buttons)
    
    await callback.answer()



#  DIVORCE COMMAND


@Client.on_message(filters.command(["divorce"], config.COMMAND_PREFIX))
async def divorce_command(client: Client, message: Message):
    """Divorce your current waifu"""
    user = message.from_user
    
    marriage = db.get_user_marriage(user.id)
    
    if not marriage or not marriage.get("married_to"):
        await message.reply_text(
            "💔 **You're not married!**\n\n"
            "Use `/marry` to propose to someone first!"
        )
        return
    
    name = marriage.get("waifu_name", "Unknown")
    emoji = get_rarity_emoji(marriage.get("waifu_rarity", "common"))
    
    text = f"""
💔 **Confirm Divorce**

Are you sure you want to divorce **{name}**?

{emoji} She will be heartbroken... 😢

⚠️ **Note:** She will stay in your collection, just unmarried.
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💔 Yes, Divorce", callback_data=f"divyes_{user.id}"),
            InlineKeyboardButton("❤️ No, Stay", callback_data=f"divno_{user.id}")
        ]
    ])
    
    await message.reply_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex(r"^divcon_(\d+)$"))
async def divorce_confirm_callback(client: Client, callback: CallbackQuery):
    """Show divorce confirmation from wife view"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your marriage!", show_alert=True)
        return
    
    marriage = db.get_user_marriage(owner_id)
    
    if not marriage:
        await callback.answer("❌ You're not married!", show_alert=True)
        return
    
    name = marriage.get("waifu_name", "Unknown")
    emoji = get_rarity_emoji(marriage.get("waifu_rarity", "common"))
    
    text = f"""
💔 **Confirm Divorce**

Are you sure you want to divorce **{name}**?

{emoji} She will be heartbroken... 😢

⚠️ She will stay in your collection, just unmarried.
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💔 Yes, Divorce", callback_data=f"divyes_{owner_id}"),
            InlineKeyboardButton("❤️ No, Stay Married", callback_data=f"divno_{owner_id}")
        ]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except:
        pass
    
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^divyes_(\d+)$"))
async def divorce_yes_callback(client: Client, callback: CallbackQuery):
    """Confirm divorce"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your marriage!", show_alert=True)
        return
    
    marriage = db.get_user_marriage(owner_id)
    
    if not marriage:
        await callback.answer("❌ You're not married!", show_alert=True)
        return
    
    name = marriage.get("waifu_name", "Unknown")
    
    # Update stats
    try:
        stats = db.get_user_marriage_stats(owner_id) or {}
        stats["divorces"] = stats.get("divorces", 0) + 1
        db.set_user_marriage_stats(owner_id, stats)
    except:
        pass
    
    db.clear_user_marriage(owner_id)
    
    text = f"""
💔 **Divorced**

You and **{name}** are no longer married.

😢 She's crying but she's still in your collection...

💡 Use `/marry` when you're ready to love again!
"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💒 Find New Love", callback_data=f"startm_{owner_id}")]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except:
        pass
    
    await callback.answer("💔 Divorced...")


@Client.on_callback_query(filters.regex(r"^divno_(\d+)$"))
async def divorce_no_callback(client: Client, callback: CallbackQuery):
    """Cancel divorce"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not your marriage!", show_alert=True)
        return
    
    await callback.answer("❤️ Good choice! She loves you!")
    
    try:
        await callback.message.delete()
    except:
        pass


# ═══════════════════════════════════════════════════════════════════
# 💒 START MARRY CALLBACK
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^startm_(\d+)$"))
async def start_marry_callback(client: Client, callback: CallbackQuery):
    """Start marry from callback"""
    try:
        owner_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid data!", show_alert=True)
        return
    
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Not for you!", show_alert=True)
        return
    
    await callback.answer()
    
    try:
        await callback.message.delete()
    except:
        pass
    
    # Check if already in proposal
    if owner_id in active_proposals:
        await callback.message.reply_text(
            "❌ **You already have an active proposal!**\n"
            "Complete or cancel it first."
        )
        return
    
    # Check if married
    marriage = db.get_user_marriage(owner_id)
    if marriage and marriage.get("married_to"):
        waifu_name = marriage.get("waifu_name", "your waifu")
        await callback.message.reply_text(
            f"💒 **You're already married to {waifu_name}!**\n\n"
            f"Use `/divorce` first if you want to marry someone else."
        )
        return
    
    # Check cooldown
    last_marry = db.get_user_data(owner_id, "last_marry_attempt")
    if last_marry:
        try:
            last_time = datetime.fromisoformat(last_marry)
            elapsed = (datetime.now() - last_time).total_seconds()
            remaining = MARRY_COOLDOWN - elapsed
            
            if remaining > 0:
                await callback.message.reply_text(
                    f"⏳ **Marriage Cooldown!**\n\n"
                    f"You can propose again in **{format_time_remaining(int(remaining))}**"
                )
                return
        except:
            pass
    
    # Get collection
    collection = db.get_full_collection(owner_id)
    
    if not collection:
        await callback.message.reply_text(
            "❌ **Your collection is empty!**\n\n"
            "Use `/smash` to collect some waifus first! 💕"
        )
        return
    
    unique_waifus = get_unique_waifus(collection)
    
    if not unique_waifus:
        await callback.message.reply_text("❌ No valid waifus in your collection!")
        return
    
    # Store proposal
    active_proposals[owner_id] = {
        "waifus": unique_waifus,
        "stage": "selecting",
        "page": 0,
        "rarity": None
    }
    
    keyboard = build_marry_keyboard(owner_id, unique_waifus, 0, None)
    
    text = """
💒 **Marriage Proposal**

Choose a waifu from your collection to propose to!

⚠️ **WARNING:** 
If she **rejects** your proposal, you will **LOSE** her from your collection forever!

👇 Select your waifu:
"""
    
    try:
        await callback.message.reply_photo(
            photo=MARRY_DEFAULT_IMAGE,
            caption=text,
            reply_markup=keyboard
        )
    except:
        await callback.message.reply_text(text, reply_markup=keyboard)


# ═══════════════════════════════════════════════════════════════════
# 🔧 ADMIN: CLEAR COOLDOWN
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["clearmarrycd", "resetmarry"], config.COMMAND_PREFIX))
async def clear_marry_cooldown(client: Client, message: Message):
    """Owner only - clear marry cooldown"""
    user = message.from_user
    
    sudo_users = getattr(config, 'SUDO_USERS', [])
    if user.id != config.OWNER_ID and user.id not in sudo_users:
        return await message.reply_text("❌ Owner only command!")
    
    target = extract_target_user(message)
    
    if not target:
        return await message.reply_text(
            "❌ **Target missing!**\n\n"
            "Reply to user / tag user / give user_id\n\n"
            "`/clearmarrycd @user`\n"
            "`/clearmarrycd 123456789`"
        )
    
    target_id = target if isinstance(target, int) else target.id
    
    db.set_user_data(target_id, "last_marry_attempt", None)
    
    await message.reply_text(
        f"✅ **Marriage cooldown cleared!**\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"💒 User can now `/marry` immediately."
    )


# ═══════════════════════════════════════════════════════════════════
# 📊 MARRIAGE STATS COMMAND
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["marriages", "marriagestats"], config.COMMAND_PREFIX))
async def marriages_command(client: Client, message: Message):
    """View marriage statistics"""
    user = message.from_user
    
    stats = db.get_user_marriage_stats(user.id) or {}
    marriage = db.get_user_marriage(user.id)
    
    total_proposals = stats.get("total_proposals", 0)
    accepted = stats.get("accepted", 0)
    rejected = stats.get("rejected", 0)
    divorces = stats.get("divorces", 0)
    
    current_wife = "None 💔"
    if marriage and marriage.get("married_to"):
        emoji = get_rarity_emoji(marriage.get("waifu_rarity", "common"))
        current_wife = f"{emoji} {marriage.get('waifu_name', 'Unknown')}"
    
    success_rate = (accepted / total_proposals * 100) if total_proposals > 0 else 0
    
    text = f"""
📊 **Marriage Statistics**

👤 **{user.first_name}**
━━━━━━━━━━━━━━━━━━━

💒 **Current Wife:** {current_wife}

📈 **Stats:**
💍 Total Proposals: {total_proposals}
✅ Accepted: {accepted}
❌ Rejected: {rejected}
💔 Divorces: {divorces}

💡 Success Rate: {success_rate:.1f}%
"""
    
    await message.reply_text(text)


print("✅ [MARRY] Module loaded successfully!")
