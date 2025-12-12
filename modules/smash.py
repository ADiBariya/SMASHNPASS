# modules/smash.py - Main Game Module with Strict Force Sub & Sexy Captions
# FIXED AUTO-DELETE SYSTEM

import random
import asyncio
import time
import json
import os
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.errors import FloodWait, UserNotParticipant
from database import db
from helpers import get_waifu_manager, Utils
import config

# Module info
__MODULE__ = "Smash"
__HELP__ = """
🎮 **Smash Game**

**Commands:**
/smash - Start a new game
/waifu - Same as smash
/sp - Short command

**Admin Commands:**
/autodel <seconds> - Set auto-delete time (10-300)
/autodel off - Disable auto-delete
/autodelstatus - Check current setting
"""

# FORCE SUBSCRIPTION SETTINGS
SUPPORT_CHAT = "@Waifusmashsupport"  # Your support chat username (change this)
SUPPORT_CHAT_ID = -1003494497037  # Your support chat ID (change this)

# Store active games {user_id: waifu_data}
active_games = {}

# Track recently shown waifus per user
recent_waifus = {}

# Track last pass time to prevent spam
last_pass_time = {}

# Default auto-delete time
DEFAULT_AUTO_DELETE = 30

# Auto-delete settings file
AUTO_DELETE_FILE = "auto_delete_settings.json"

# In-memory cache for auto-delete settings
auto_delete_cache = {}

#ye jo bhi ho tuje kya bhai
async def smash_active(message: Message, pending: bool = True) -> bool:
    """Check if user already has an active smash game"""
    user_id = message.from_user.id

    if user_id in active_games:
        if pending:
            await message.reply_text(
                "❗ **You already have an active Smash game!**\n"
                "Finish it first before starting a new one."
            )
        return True
    
    return False
#han han le 
def load_auto_delete_settings():
    """Load auto-delete settings from file on startup"""
    global auto_delete_cache
    try:
        if os.path.exists(AUTO_DELETE_FILE):
            with open(AUTO_DELETE_FILE, 'r') as f:
                data = json.load(f)
                # Convert string keys back to int (JSON only supports string keys)
                auto_delete_cache = {int(k): v for k, v in data.items()}
                print(f"✅ [AUTO-DEL] Loaded {len(auto_delete_cache)} settings from file")
        else:
            auto_delete_cache = {}
            print("📁 [AUTO-DEL] No settings file found, starting fresh")
    except Exception as e:
        print(f"⚠️ [AUTO-DEL] Error loading settings: {e}")
        auto_delete_cache = {}


def save_auto_delete_settings():
    """Save auto-delete settings to file"""
    try:
        with open(AUTO_DELETE_FILE, 'w') as f:
            # Convert int keys to string for JSON compatibility
            json.dump({str(k): v for k, v in auto_delete_cache.items()}, f, indent=2)
        print(f"💾 [AUTO-DEL] Saved {len(auto_delete_cache)} settings to file")
        return True
    except Exception as e:
        print(f"❌ [AUTO-DEL] Error saving settings: {e}")
        return False


def get_auto_delete_time(chat_id: int) -> int:
    """Get auto-delete time for a chat"""
    return auto_delete_cache.get(chat_id, DEFAULT_AUTO_DELETE)


def set_auto_delete_time(chat_id: int, seconds: int) -> bool:
    """Set auto-delete time for a chat and save to file"""
    try:
        auto_delete_cache[chat_id] = seconds
        save_auto_delete_settings()
        print(f"✅ [AUTO-DEL] Set chat {chat_id} to {seconds}s")
        return True
    except Exception as e:
        print(f"❌ [AUTO-DEL] Error setting time: {e}")
        return False


async def auto_delete_message(message: Message, delay: int):
    """Delete message after delay with proper error handling"""
    if delay <= 0:
        return
    
    try:
        print(f"🗑️ [AUTO-DEL] Scheduling delete in {delay}s for message {message.id}")
        await asyncio.sleep(delay)
        await message.delete()
        print(f"✅ [AUTO-DEL] Deleted message {message.id} successfully")
    except Exception as e:
        print(f"⚠️ [AUTO-DEL] Could not delete message {message.id}: {e}")


async def schedule_auto_delete(message: Message, chat_id: int) -> int:
    """Schedule auto-delete for a message and return the delay"""
    delete_time = get_auto_delete_time(chat_id)
    
    if delete_time > 0:
        asyncio.create_task(auto_delete_message(message, delete_time))
        return delete_time
    
    return 0


def format_delete_time(seconds: int) -> str:
    """Format seconds into readable time string"""
    if seconds <= 0:
        return "Disabled"
    elif seconds >= 60:
        mins = seconds // 60
        secs = seconds % 60
        if secs:
            return f"{mins}m {secs}s"
        return f"{mins} minute(s)"
    else:
        return f"{seconds} seconds"


# Load settings on module import
load_auto_delete_settings()


# ═══════════════════════════════════════════════════════════════════
#  🔥 SEXY CAPTION GENERATORS (WITHOUT POWER & BORDERS)
# ═══════════════════════════════════════════════════════════════════

def get_smash_loading_caption(waifu_name: str) -> str:
    """Get sexy loading caption"""
    captions = [
        f"💥 **SMASHING YOUR BADDIE...**\n\n"
        f"Getting close to **{waifu_name}**... 😏🔥",
        
        f"🔥 **MAKING MOVES...**\n\n"
        f"Shooting your shot at **{waifu_name}**... 💋",
        
        f"💋 **RIZZING UP...**\n\n"
        f"Working your magic on **{waifu_name}**... ✨",
        
        f"😈 **SLIDING INTO DMs...**\n\n"
        f"Charming **{waifu_name}**... 💕",
        
        f"🌹 **SMOOTH OPERATOR...**\n\n"
        f"Wooing **{waifu_name}** with your charm... 😘",
        
        f"💫 **MAIN CHARACTER MOMENT...**\n\n"
        f"Making **{waifu_name}** fall for you... 🦋",
    ]
    return random.choice(captions)


def get_win_caption(waifu: dict, coins: int) -> str:
    """Get sexy win caption"""
    name = waifu.get('name', 'Unknown')
    anime = waifu.get('anime', 'Unknown')
    rarity = waifu.get('rarity', 'common').title()
    
    win_headers = [
        f"🔥 **SHE'S ALL YOURS NOW!**",
        f"💋 **YOU SMASHED IT!**",
        f"😈 **BADDIE ACQUIRED!**",
        f"💕 **SHE SAID YES!**",
        f"🎉 **RIZZ GOD ENERGY!**",
        f"✨ **SMOOTH CRIMINAL!**",
        f"💥 **SMASH SUCCESSFUL!**",
        f"🦋 **SHE FELL FOR YOU!**",
    ]
    
    win_messages = [
        f"**{name}** couldn't resist your charm! 😏",
        f"**{name}** is now your waifu! No cap! 🔥",
        f"**{name}** joined your collection, king! 👑",
        f"**{name}** said \"take me home\"! 💋",
        f"You pulled **{name}** with that rizz! 😎",
        f"**{name}** is down bad for you now! 💕",
        f"**{name}** got swept off her feet! ✨",
        f"Main character moment with **{name}**! 🌟",
    ]
    
    header = random.choice(win_headers)
    message = random.choice(win_messages)
    
    return f"""
{header}

{message}

📺 **Anime:** {anime}
💎 **Rarity:** {rarity}
💰 **Coins:** +{coins}

Use /collection to see your baddies! 😈
"""


def get_lose_caption(waifu: dict) -> str:
    """Get rejection caption"""
    name = waifu.get('name', 'Unknown')
    
    lose_headers = [
        f"💔 **REJECTED!**",
        f"😭 **SHE CURVED YOU!**",
        f"💀 **NO RIZZ DETECTED!**",
        f"😬 **FRIENDZONED!**",
        f"🚫 **BLOCKED & REPORTED!**",
        f"📉 **RIZZ FAILED!**",
        f"😢 **LEFT ON READ!**",
        f"🥶 **COLD SHOULDER!**",
    ]
    
    lose_messages = [
        f"**{name}** said \"ew, no thanks\" 💀",
        f"**{name}** left you on seen... 📱",
        f"**{name}** chose violence today 😤",
        f"**{name}** activated airplane mode ✈️",
        f"**{name}** said you're not her type 🙅‍♀️",
        f"**{name}** ran away screaming 🏃‍♀️",
        f"**{name}** called security on you 👮",
        f"**{name}** pretended she didn't see you 👀",
    ]
    
    tips = [
        "Maybe try being less down bad? 🤔",
        "Legendary waifus have high standards! 👑",
        "Your rizz needs work, bro 💪",
        "Keep grinding, king! 🔥",
        "Not every baddie can be yours 😤",
        "L today, W tomorrow! 📈",
        "Practice makes perfect! ✨",
        "The grind never stops! 💯",
    ]
    
    header = random.choice(lose_headers)
    message = random.choice(lose_messages)
    tip = random.choice(tips)
    
    return f"""
{header}

{message}

**Tip:** {tip}
"""


def get_waifu_intro_caption(waifu: dict, is_passed: bool = False) -> str:
    """Get intro caption for waifu"""
    name = waifu.get('name', 'Unknown')
    anime = waifu.get('anime', 'Unknown')
    rarity = waifu.get('rarity', 'common').title()
    
    # Get rarity emoji
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵", 
        "epic": "🟣",
        "legendary": "🟡"
    }
    rarity_emoji = rarity_emojis.get(waifu.get('rarity', 'common'), "⚪")
    
    if is_passed:
        headers = [
            "👋 **Passed! Here's another baddie:**",
            "👀 **Next one up:**",
            "🔄 **Alright, check this one:**",
            "✨ **New challenger appeared:**",
            "🎲 **Rolling again... look who showed up:**",
        ]
        header = random.choice(headers)
    else:
        headers = [
            "🔥 **A wild baddie appeared!**",
            "✨ **Look who showed up!**",
            "👀 **Ayo check this one out:**",
            "💫 **New waifu alert!**",
            "😳 **She's looking at you:**",
            "🎯 **Target acquired:**",
        ]
        header = random.choice(headers)
    
    flirt_lines = [
        "She's waiting for your move... 😏",
        "What's it gonna be, chief? 🤔",
        "You feeling lucky, punk? 🎰",
        "Do you have what it takes? 💪",
        "She's kinda bad tho... 👀",
        "Your call, player 🎮",
        "Smash or pass, no cap 🧢",
        "The choice is yours 🔥",
    ]
    
    return f"""
{header}

{rarity_emoji} **{name}**

📺 **Anime:** {anime}
💎 **Rarity:** {rarity}

{random.choice(flirt_lines)}
"""


# ═══════════════════════════════════════════════════════════════════
#  🔒 STRICT FORCE SUBSCRIPTION CHECKER
# ═══════════════════════════════════════════════════════════════════

async def check_subscription(client: Client, user_id: int) -> bool:
    """Check if user is CURRENTLY subscribed to support chat"""
    try:
        # Get current member status
        member = await client.get_chat_member(SUPPORT_CHAT_ID, user_id)
        
        # Check if user is actually in the chat (not left or kicked)
        if member.status in ["left", "kicked", "banned"]:
            print(f"❌ [SUB CHECK] User {user_id} status: {member.status}")
            return False
        
        # User is member, admin, or creator
        print(f"✅ [SUB CHECK] User {user_id} is subscribed: {member.status}")
        return True
        
    except UserNotParticipant:
        print(f"❌ [SUB CHECK] User {user_id} not in chat")
        return False
        
    except Exception as e:
        print(f"⚠️ [SUB CHECK] Error checking {user_id}: {e}")
        # Return False on error to be safe
        return False


def get_force_sub_message(waifu_name: str = None) -> str:
    """Get force subscription message"""
    messages = [
        f"""
❌ **Oops! You Left My Support Chat!**

Bro really thought they could leave and still play? 💀
Join back to continue hunting baddies! 🔥
""",
        f"""
❌ **Access Denied!**

You need to stay in my support chat to play! 
No support = No baddies! 😤
""",
        f"""
❌ **Caught You Lacking!**

Join my support chat first, then come back! 
The baddies are waiting... 👀
""",
    ]
    
    if waifu_name:
        messages.append(f"""
❌ **Hold Up!**

**{waifu_name}** says join my support first! 
She doesn't talk to non-members 🙅‍♀️
""")
    
    return random.choice(messages)


# ═══════════════════════════════════════════════════════════════════
#  🔥 SEXY PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════

async def show_progress_bar(callback: CallbackQuery, waifu_name: str, is_win: bool):
    """Show sexy progress bar animation"""
    
    progress_stages = [
        "💋 Shooting your shot...\n▱▱▱▱▱▱▱▱▱▱ 0%",
        "😏 Getting closer...\n▰▰▱▱▱▱▱▱▱▱ 20%",
        "🔥 She's looking...\n▰▰▰▰▱▱▱▱▱▱ 40%",
        "💕 Making eye contact...\n▰▰▰▰▰▰▱▱▱▱ 60%",
        "😈 Going in for it...\n▰▰▰▰▰▰▰▰▱▱ 80%",
        "💥 SMASHING...\n▰▰▰▰▰▰▰▰▰▰ 100%",
    ]
    
    for stage in progress_stages:
        try:
            await callback.answer(stage, show_alert=False)
            await asyncio.sleep(0.4)
        except:
            pass
    
    # Final result popup
    if is_win:
        results = [
            f"🔥 SHE'S YOURS! {waifu_name} joined you!",
            f"💋 SMASHED! {waifu_name} is down bad!",
            f"😈 W RIZZ! {waifu_name} fell for you!",
            f"✨ BADDIE GET! {waifu_name} acquired!",
        ]
        await callback.answer(random.choice(results), show_alert=True)
    else:
        rejects = [
            f"💔 REJECTED! {waifu_name} said no way!",
            f"💀 L + RATIO! {waifu_name} curved you!",
            f"😭 NO RIZZ! {waifu_name} ran away!",
            f"🚫 DENIED! {waifu_name} blocked you!",
        ]
        await callback.answer(random.choice(rejects), show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  🛡️ FLOOD WAIT HANDLER
# ═══════════════════════════════════════════════════════════════════

async def safe_edit_message(callback: CallbackQuery, text: str = None, caption: str = None, 
                           reply_markup=None, media=None, retry_count: int = 3):
    """Safely edit message with flood wait handling"""
    
    for attempt in range(retry_count):
        try:
            if media:
                return await callback.message.edit_media(media=media, reply_markup=reply_markup)
            elif callback.message.photo and caption:
                return await callback.message.edit_caption(caption=caption, reply_markup=reply_markup)
            elif text:
                return await callback.message.edit_text(text=text, reply_markup=reply_markup)
                
        except FloodWait as e:
            wait_time = min(e.value, 10)
            print(f"⏳ [FLOOD] Waiting {wait_time}s due to rate limit...")
            
            if wait_time <= 5:
                await asyncio.sleep(wait_time)
            else:
                await callback.answer(
                    f"⏳ Too many actions! Wait {wait_time}s...",
                    show_alert=True
                )
                return None
                
        except Exception as e:
            print(f"⚠️ [EDIT] Error on attempt {attempt + 1}: {e}")
            if attempt == retry_count - 1:
                return None
    
    return None


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

async def is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check admin with FULL Telegram status support"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [
            "administrator",
            "creator",
            "owner",
            "chat_administrator"
        ]
    except:
        return False


def get_unique_waifu(wm, user_id: int):
    """Get a waifu that hasn't been shown recently"""
    
    if user_id not in recent_waifus:
        recent_waifus[user_id] = []
    
    recent_list = recent_waifus[user_id]
    max_attempts = 50
    
    for _ in range(max_attempts):
        all_waifus = wm.get_all_waifus()       # ✅ merged JSON + TG waifus
        waifu = random.choice(all_waifus)

        if not waifu:
            return None
        
        waifu_id = waifu.get("id")
        
        if waifu_id not in recent_list:
            recent_list.append(waifu_id)
            if len(recent_list) > 10:
                recent_list.pop(0)
            return waifu
    
    return wm.get_random_waifu()


def can_pass_again(user_id: int) -> tuple:
    """Check if user can pass again (anti-spam)"""
    current_time = time.time()
    
    if user_id in last_pass_time:
        time_diff = current_time - last_pass_time[user_id]
        if time_diff < 2:
            return False, int(2 - time_diff)
    
    return True, 0


# ═══════════════════════════════════════════════════════════════════
#  🔧 AUTO-DELETE ADMIN COMMANDS (FIXED)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["autodel", "autodelete"]) & filters.group)
async def set_auto_delete_cmd(client: Client, message: Message):
    """Set auto-delete time for the group with Robust Admin Check"""
    user = message.from_user
    chat_id = message.chat.id

    if not user: # Handle anonymous admins
        return

    # 🛡️ ROBUST ADMIN CHECK
    try:
        member = await client.get_chat_member(chat_id, user.id)
        
        # Convert status to string and lowercase to be safe
        status = str(member.status).split('.')[-1].lower() 
        
        # Check against all possible admin strings
        is_admin = status in ["administrator", "creator", "owner"]
        
        if not is_admin:
            print(f"🚫 [ADMIN CHECK] Denied: User {user.id} status is {status}")
            reply = await message.reply_text("❌ **Only admins can change auto-delete settings!**")
            await asyncio.sleep(5)
            try:
                await reply.delete()
                await message.delete()
            except: pass
            return
            
    except Exception as e:
        print(f"⚠️ [AUTODEL] Admin verify failed: {e}")
        # Fallback: if we can't verify, don't allow changes
        await message.reply_text("❌ **Unable to verify your admin status. Please make sure I have permission to see members!**")
        return
# Get arguments
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if not args:
        current = get_auto_delete_time(chat_id)
        status = format_delete_time(current)
        
        await message.reply_text(
            f"🗑️ **Auto-Delete Settings**\n\n"
            f"**Current:** {status}\n\n"
            f"**Usage:**\n"
            f"• `/autodel <10-300>` - Set seconds\n"
            f"• `/autodel off` - Disable auto-delete\n\n"
            f"**Examples:**\n"
            f"• `/autodel 30` - Delete after 30s\n"
            f"• `/autodel 60` - Delete after 1 min\n"
            f"• `/autodel off` - Keep messages"
        )
        return

    value = args[0].lower()

    # Handle disable
    if value in ["off", "0", "disable", "no", "false"]:
        success = set_auto_delete_time(chat_id, 0)
        
        if success:
            await message.reply_text(
                "🗑️ **Auto-Delete Disabled!**\n\n"
                "Game messages will no longer be deleted automatically."
            )
        else:
            await message.reply_text("❌ **Failed to update settings!**")
        return

    # Handle number
    try:
        seconds = int(value)
    except ValueError:
        await message.reply_text(
            "❌ **Invalid value!**\n\n"
            "Use a number between 10-300 or `off`"
        )
        return

    # Validate range
    if seconds < 10 or seconds > 300:
        await message.reply_text(
            "❌ **Value out of range!**\n\n"
            "Must be between **10 - 300 seconds**\n"
            "Use `/autodel off` to disable"
        )
        return

    # Set the value
    success = set_auto_delete_time(chat_id, seconds)
    
    if success:
        time_str = format_delete_time(seconds)
        await message.reply_text(
            f"✅ **Auto-Delete Enabled!**\n\n"
            f"🗑️ Game messages will be deleted after **{time_str}**"
        )
    else:
        await message.reply_text("❌ **Failed to update settings!**")


@Client.on_message(filters.command(["autodelstatus", "delstatus", "adstatus"]) & filters.group)
async def auto_delete_status_cmd(client: Client, message: Message):
    """Check current auto-delete status"""
    chat_id = message.chat.id
    current = get_auto_delete_time(chat_id)

    if current == 0:
        status_text = (
            "🗑️ **Auto-Delete Status**\n\n"
            "**Status:** ❌ Disabled\n\n"
            "Use `/autodel <seconds>` to enable"
        )
    else:
        time_str = format_delete_time(current)
        status_text = (
            f"🗑️ **Auto-Delete Status**\n\n"
            f"**Status:** ✅ Enabled\n"
            f"**Time:** {time_str}\n\n"
            f"Use `/autodel off` to disable"
        )
    
    reply = await message.reply_text(status_text)
    
    # Auto-delete this status message too
    if current > 0:
        asyncio.create_task(auto_delete_message(reply, current))
        asyncio.create_task(auto_delete_message(message, current))


#smash Command

@Client.on_message(filters.command(["smash", "waifu", "sp"], config.COMMAND_PREFIX))
async def smash_command(client: Client, message: Message):
    """Start a new smash or pass game"""
    user = message.from_user
    chat_id = message.chat.id
    if await smash_active(message):
        return
    
    print(f"🎮 [SMASH] /smash from {user.first_name} ({user.id}) in chat {chat_id}")
    
    # 🔒 CHECK SUBSCRIPTION FIRST
    is_subscribed = await check_subscription(client, user.id)
    
    if not is_subscribed:
        force_sub_text = get_force_sub_message()
        force_sub_text += "\n\n👇 **Join now and start playing!**"
        
        force_sub_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Join Support Chat", url=f"https://t.me/{SUPPORT_CHAT.replace('@', '')}")
            ],
            [
                InlineKeyboardButton("✅ I Joined, Start Game", callback_data=f"check_and_start_{user.id}")
            ]
        ])
        
        sent = await message.reply_text(force_sub_text, reply_markup=force_sub_buttons)
        
        # Auto-delete force sub message after some time
        delete_time = get_auto_delete_time(chat_id)
        if delete_time > 0:
            asyncio.create_task(auto_delete_message(sent, delete_time))
            asyncio.create_task(auto_delete_message(message, delete_time))
        return
    
    # Continue with normal game flow if subscribed
    try:
        wm = get_waifu_manager()
    except Exception as e:
        print(f"❌ [SMASH] WaifuManager error: {e}")
        await message.reply_text(f"❌ Error loading waifus: {e}")
        return
    
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except Exception as e:
        print(f"⚠️ [SMASH] DB error: {e}")
    
    # Check cooldown
    try:
        on_cooldown, remaining = db.check_cooldown(user.id, "smash")
        if on_cooldown:
            cooldown_msg = await message.reply_text(
                f"⏳ **Chill bro!**\n\n"
                f"Wait **{Utils.format_time(remaining)}** before hunting again! 🔥"
            )
            # Auto-delete cooldown message
            delete_time = get_auto_delete_time(chat_id)
            if delete_time > 0:
                asyncio.create_task(auto_delete_message(cooldown_msg, min(delete_time, 10)))
                asyncio.create_task(auto_delete_message(message, min(delete_time, 10)))
            return
    except Exception as e:
        print(f"⚠️ [SMASH] Cooldown error: {e}")
    
    waifu = get_unique_waifu(wm, user.id)
    
    print(f"🎲 [SMASH] Got waifu: {waifu.get('name') if waifu else 'None'}")
    
    if not waifu:
        await message.reply_text(
            "❌ **No baddies available!**\n\n"
            "Admin needs to add waifus first! 😢"
        )
        return
    
    active_games[user.id] = waifu
    
    # Use sexy caption
    text = get_waifu_intro_caption(waifu, is_passed=False)
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    try:
        if image_url:
            sent = await message.reply_photo(
                photo=image_url,
                caption=text,
                reply_markup=buttons
            )
        else:
            sent = await message.reply_text(text, reply_markup=buttons)
        
        # Delete the command message
        try:
            await message.delete()
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ [SMASH] Image failed: {e}")
        sent = await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  Check and Start Game After Joining
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^check_and_start_(\d+)$"))
async def check_and_start_callback(client: Client, callback: CallbackQuery):
    """Check subscription and start game"""
    
    user_id = int(callback.data.split("_")[3])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ This button is not for you!", show_alert=True)
        return
    
    # Check if user joined
    is_subscribed = await check_subscription(client, callback.from_user.id)
    
    if not is_subscribed:
        await callback.answer(
            "❌ You haven't joined the support chat yet! Join first!",
            show_alert=True
        )
        return
    
    # Start the game
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.answer("✅ Starting game...")
    
    # Create a fake message object to trigger smash command
    callback.message.from_user = callback.from_user
    callback.message.text = "/smash"
    await smash_command(client, callback.message)


# ═══════════════════════════════════════════════════════════════════
#  Smash Button Callback with STRICT Force Sub
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^smash_(\d+)_(\d+)$"))
async def smash_callback(client: Client, callback: CallbackQuery):
    """Handle smash button with strict subscription check"""
    
    print(f"💥 [SMASH] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ Get your own baddie!", show_alert=True)
        return
    
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    # 🔒 ALWAYS CHECK SUBSCRIPTION ON EVERY SMASH
    is_subscribed = await check_subscription(client, user.id)
    
    if not is_subscribed:
        # Get waifu name for personalized message
        waifu_name = None
        if user.id in active_games:
            waifu_name = active_games[user.id].get('name')
        
        force_sub_text = get_force_sub_message(waifu_name)
        force_sub_text += "\n\n👇 **Join back to continue playing!**"
        
        force_sub_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Join Support Chat", url=f"https://t.me/{SUPPORT_CHAT.replace('@', '')}")
            ],
            [
                InlineKeyboardButton("🔄 I Joined, Try Again", callback_data=f"retry_smash_{game_user_id}_{waifu_id}")
            ]
        ])
        
        await safe_edit_message(
            callback,
            caption=force_sub_text if callback.message.photo else None,
            text=force_sub_text if not callback.message.photo else None,
            reply_markup=force_sub_buttons
        )
        
        await callback.answer("❌ You left the support chat! Join back!", show_alert=True)
        return
    
    # Continue with game if subscribed
    wm = get_waifu_manager()
    
    if user.id not in active_games:
        await callback.answer("❌ Game expired! Use /smash", show_alert=True)
        return
    
    waifu = active_games.pop(user.id)
    
    if waifu.get("id") != waifu_id:
        await callback.answer("❌ Invalid game!", show_alert=True)
        return
    
    # Calculate win
    win_chance = getattr(config, 'WIN_CHANCE', 60)
    rarity = waifu.get("rarity", "common")
    
    if rarity == "legendary":
        win_chance -= 20
    elif rarity == "epic":
        win_chance -= 10
    elif rarity == "rare":
        win_chance -= 5
    
    # Force 100% win for specific user
    if user.id == 5162885921:
        win_chance = 100
    
    is_win = Utils.calculate_win(win_chance)
    
    # Start progress animation
    asyncio.create_task(show_progress_bar(callback, waifu.get('name', 'Unknown'), is_win))
    
    # Show sexy loading caption with flood handling
    loading_text = get_smash_loading_caption(waifu.get('name', 'Unknown'))
    
    await safe_edit_message(
        callback,
        caption=loading_text if callback.message.photo else None,
        text=loading_text if not callback.message.photo else None,
        reply_markup=None
    )
    
    await asyncio.sleep(2.5)
    
    # Set cooldown
    try:
        db.set_cooldown(user.id, "smash", getattr(config, 'GAME_COOLDOWN', 30))
    except:
        pass
    
    # Update stats
    try:
        db.increment_user_stats(user.id, "total_smash")
    except:
        pass
    
    print(f"🎲 [SMASH] Chance: {win_chance}%, Result: {'WIN' if is_win else 'LOSE'}")
    
    # Get delete time and format notice
    delete_time = get_auto_delete_time(chat_id)
    delete_notice = f"\n\n🗑️ __Auto-deleting in {format_delete_time(delete_time)}__" if delete_time > 0 else ""
    
    if is_win:
        try:
            db.increment_user_stats(user.id, "total_wins")
        except:
            pass
        
        # Get coins
        try:
            if hasattr(wm, 'rarity_points'):
                coins = wm.rarity_points.get(rarity, 500)
            else:
                coins = {"common": 500, "epic": 1500,  "legendary": 3000, "rare": 5000}.get(rarity, 500)
        except:
            coins = {"common": 500, "epic": 1500,  "legendary": 3000, "rare": 5000}.get(rarity, 500)
        
        try:
            db.add_coins(user.id, coins)
        except:
            pass
        
        try:
            db.add_waifu_to_collection(user.id, waifu)
        except Exception as e:
            print(f"⚠️ [SMASH] Collection error: {e}")
        
        text = get_win_caption(waifu, coins) + delete_notice
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔥 HUNT AGAIN", callback_data="play_smash"),
                InlineKeyboardButton("📦 MY BADDIES", callback_data="view_collection")
            ]
        ])
        
    else:
        try:
            db.increment_user_stats(user.id, "total_losses")
        except:
            pass
        
        text = get_lose_caption(waifu) + delete_notice
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Try Again", callback_data="play_smash")
            ]
        ])
    
    # Update message with flood handling
    result = await safe_edit_message(
        callback,
        caption=text if callback.message.photo else None,
        text=text if not callback.message.photo else None,
        reply_markup=buttons
    )
    
    # Schedule auto-delete
    if result and delete_time > 0:
        asyncio.create_task(auto_delete_message(callback.message, delete_time))
        print(f"🗑️ [SMASH] Scheduled delete in {delete_time}s for chat {chat_id}")


# ═══════════════════════════════════════════════════════════════════
#  Retry Smash After Re-Joining Support
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^retry_smash_(\d+)_(\d+)$"))
async def retry_smash_callback(client: Client, callback: CallbackQuery):
    """Handle retry after re-joining support"""
    
    data = callback.data.split("_")
    game_user_id = int(data[2])
    waifu_id = int(data[3])
    
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ Not your game!", show_alert=True)
        return
    
    user = callback.from_user
    
    # Check subscription again
    is_subscribed = await check_subscription(client, user.id)
    
    if not is_subscribed:
        await callback.answer(
            "❌ You STILL haven't joined the support chat! Join first!",
            show_alert=True
        )
        return
    
    await callback.answer("✅ Welcome back! Let's continue...")
    
    # Restore the game if waifu still in active_games
    if user.id not in active_games:
        # Since we can't get exact waifu back, just start new game
        callback.data = "play_smash"
        await play_smash_callback(client, callback)
    else:
        # If game still active, redirect to smash
        callback.data = f"smash_{game_user_id}_{waifu_id}"
        await smash_callback(client, callback)


# ═══════════════════════════════════════════════════════════════════
#  Pass Button Callback (Check sub for next waifu)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pass_(\d+)_(\d+)$"))
async def pass_callback(client: Client, callback: CallbackQuery):
    """Handle pass button - but check sub for next waifu"""
    
    print(f"👋 [PASS] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ Not your game!", show_alert=True)
        return
    
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    # Anti-spam check
    can_pass, wait_time = can_pass_again(user.id)
    if not can_pass:
        await callback.answer(
            f"⏳ Too fast! Wait {wait_time}s between passes.",
            show_alert=False
        )
        return
    
    # Update last pass time
    last_pass_time[user.id] = time.time()
    
    wm = get_waifu_manager()
    
    if user.id in active_games:
        active_games.pop(user.id)
    
    try:
        db.increment_user_stats(user.id, "total_pass")
    except:
        pass
    
    waifu = get_unique_waifu(wm, user.id)
    
    if not waifu:
        await callback.answer("❌ No more baddies!", show_alert=True)
        return
    
    active_games[user.id] = waifu
    
    # Sexy pass caption
    text = get_waifu_intro_caption(waifu, is_passed=True)
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    # Try to edit with flood handling
    result = await safe_edit_message(
        callback,
        caption=text if callback.message.photo else None,
        text=text if not callback.message.photo else None,
        reply_markup=buttons,
        media=InputMediaPhoto(media=image_url, caption=text) if image_url and callback.message.photo else None
    )
    
    if result:
        pass_responses = [
            "👋 Next baddie loading...",
            "🔄 Alright, check this one!",
            "👀 Here's another one!",
            "✨ New challenger!",
        ]
        await callback.answer(random.choice(pass_responses))
    else:
        # If edit failed due to flood, send new message
        try:
            await callback.message.delete()
            if image_url:
                await callback.message.reply_photo(
                    photo=image_url,
                    caption=text,
                    reply_markup=buttons
                )
            else:
                await callback.message.reply_text(text, reply_markup=buttons)
            await callback.answer("👋 Passed! (New message due to rate limit)")
        except:
            await callback.answer("⚠️ Too many actions! Wait a moment.", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  Play Again Callback with Force Sub Check
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^play_smash$"))
async def play_smash_callback(client: Client, callback: CallbackQuery):
    """Handle play smash button with sub check"""
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    print(f"🎮 [PLAY] Callback from {user.first_name}")
    
    # 🔒 CHECK SUBSCRIPTION EVERY TIME
    is_subscribed = await check_subscription(client, user.id)
    
    if not is_subscribed:
        force_sub_text = get_force_sub_message()
        force_sub_text += "\n\n👇 **Join back to keep playing!**"
        
        force_sub_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Join Support Chat", url=f"https://t.me/{SUPPORT_CHAT.replace('@', '')}")
            ],
            [
                InlineKeyboardButton("✅ I Joined, Continue", callback_data=f"check_play_{user.id}")
            ]
        ])
        
        await safe_edit_message(
            callback,
            caption=force_sub_text if callback.message.photo else None,
            text=force_sub_text if not callback.message.photo else None,
            reply_markup=force_sub_buttons
        )
        
        await callback.answer("❌ Join support chat to continue!", show_alert=True)
        return
    
    # Continue with game
    wm = get_waifu_manager()
    
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except:
        pass
    
    try:
        on_cooldown, remaining = db.check_cooldown(user.id, "smash")
        if on_cooldown:
            await callback.answer(
                f"⏳ Chill! Wait {Utils.format_time(remaining)}",
                show_alert=True
            )
            return
    except:
        pass
    
    waifu = get_unique_waifu(wm, user.id)
    
    if not waifu:
        await callback.answer("❌ No baddies available!", show_alert=True)
        return
    
    active_games[user.id] = waifu
    
    text = get_waifu_intro_caption(waifu, is_passed=False)
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    # Try to edit with flood handling
    if callback.message.photo and image_url:
        # Edit media
        result = await safe_edit_message(
            callback,
            media=InputMediaPhoto(media=image_url, caption=text),
            reply_markup=buttons
        )
    else:
        result = await safe_edit_message(
            callback,
            caption=text if callback.message.photo else None,
            text=text if not callback.message.photo else None,
            reply_markup=buttons
        )
    
    if result:
        start_responses = [
            "🎮 Let's hunt some baddies!",
            "🔥 New game started!",
            "💥 Time to smash!",
            "😈 Let's get it!",
        ]
        await callback.answer(random.choice(start_responses))
    else:
        # If edit failed, send new message
        try:
            await callback.message.delete()
        except:
            pass
        
        try:
            if image_url:
                await callback.message.reply_photo(
                    photo=image_url,
                    caption=text,
                    reply_markup=buttons
                )
            else:
                await callback.message.reply_text(text, reply_markup=buttons)
            await callback.answer("🎮 New game! (Fresh message due to rate limit)")
        except Exception as e:
            print(f"❌ [PLAY] Error: {e}")
            await callback.answer("❌ Error! Try /smash command", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  Check and Play After Re-Joining
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^check_play_(\d+)$"))
async def check_play_callback(client: Client, callback: CallbackQuery):
    """Check subscription and continue playing"""
    
    user_id = int(callback.data.split("_")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ This button is not for you!", show_alert=True)
        return
    
    # Check if user joined
    is_subscribed = await check_subscription(client, callback.from_user.id)
    
    if not is_subscribed:
        await callback.answer(
            "❌ You STILL haven't joined! Join the support chat first!",
            show_alert=True
        )
        return
    
    await callback.answer("✅ Welcome back! Let's continue...")
    
    # Continue with play_smash
    callback.data = "play_smash"
    await play_smash_callback(client, callback)


# ═══════════════════════════════════════════════════════════════════
#  View Collection Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^view_collection$"))
async def view_collection_callback(client: Client, callback: CallbackQuery):
    """Handle view collection button"""
    user = callback.from_user
    
    try:
        # Get user's collection from database
        collection = db.get_user_collection(user.id)
        
        if not collection or len(collection) == 0:
            await callback.answer("📦 Your collection is empty! Start smashing!", show_alert=True)
            return
        
        # Format collection message
        collection_text = f"📦 **{user.first_name}'s Collection**\n\n"
        collection_text += f"**Total Waifus:** {db.get_collection_count(user.id)}\n\n"
        
        # Show last 5 waifus
        recent = collection[-5:] if len(collection) > 5 else collection
        collection_text += "**Recent Catches:**\n"
        
        for waifu in reversed(recent):
            rarity_emojis = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🟡"}
            emoji = rarity_emojis.get(waifu.get('rarity', 'common'), "⚪")
            collection_text += f"{emoji} {waifu.get('name', 'Unknown')}\n"
        
        collection_text += f"\nUse `/collection` for full list!"
        
        await callback.answer("📦 Opening collection...", show_alert=False)
        
        # Edit message to show collection
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔥 Hunt More", callback_data="play_smash"),
                InlineKeyboardButton("🔙 Back", callback_data="play_smash")
            ]
        ])
        
        await safe_edit_message(
            callback,
            caption=collection_text if callback.message.photo else None,
            text=collection_text if not callback.message.photo else None,
            reply_markup=buttons
        )
        
    except Exception as e:
        print(f"❌ [COLLECTION] Error: {e}")
        await callback.answer("❌ Error loading collection!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  Module Initialization
# ═══════════════════════════════════════════════════════════════════

print("✅ [SMASH] Module loaded successfully!")
print(f"📁 [SMASH] Auto-delete settings file: {AUTO_DELETE_FILE}")
print(f"🗑️ [SMASH] Default auto-delete: {DEFAULT_AUTO_DELETE}s")
print(f"💬 [SMASH] Support chat: {SUPPORT_CHAT}")
