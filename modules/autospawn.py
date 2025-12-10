# modules/auto_spawn.py - Auto Spawn System with Auto-Delete After Any Smash

import random
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from database import db
from helpers import get_waifu_manager, Utils
import config

# Module info
__MODULE__ = "AutoSpawn"
__HELP__ = """
🎲 **Auto Spawn System**

Waifus automatically spawn in group chats!

**How it works:**
• Baddies spawn based on chat activity
• First person to click SMASH gets to try
• You either WIN or LOSE - no second chances!
• Rarer baddies are harder to catch
• Spawns expire in 40 seconds
• ALL smashed waifus auto-delete after 10 seconds (win or lose)

**Admin Commands:**
/setspawn <setting> <value> - Change spawn settings
/spawnsettings - View current settings
/togglespawn - Enable/Disable auto spawn
/forcespawn - Force spawn a waifu
"""

# ═══════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════

DEFAULT_SETTINGS = {
    "enabled": True,
    "min_messages": 10,
    "max_messages": 50,
    "min_users": 2,
    "cooldown": 120,
    "expiry": 40,
    "auto_delete_after_smash": 10  # Auto-delete after 10 seconds (win OR lose)
}

SETTING_LIMITS = {
    "min_messages": (5, 100),
    "max_messages": (20, 200),
    "min_users": (1, 10),
    "cooldown": (30, 600),
    "auto_delete_after_smash": (5, 60)  # 5-60 seconds
}

RARITY_THRESHOLDS = {
    "legendary": 80,
    "epic": 50,
    "rare": 25,
    "common": 0
}

WIN_CHANCES = {
    "common": 70,
    "rare": 25,
    "epic": 55,
    "legendary": 40
}

# ═══════════════════════════════════════════════════════════════════
#  Data Storage
# ═══════════════════════════════════════════════════════════════════

group_settings = {}
group_activity = {}
active_spawns = {}  # {chat_id: spawn_data}


# ═══════════════════════════════════════════════════════════════════
#  🔥 SEXY CAPTION GENERATORS
# ═══════════════════════════════════════════════════════════════════

def get_spawn_caption(waifu: dict, activity_level: str, win_chance: int) -> str:
    """Get sexy spawn caption"""
    
    name = waifu.get('name', 'Unknown')
    anime = waifu.get('anime', 'Unknown')
    rarity = waifu.get('rarity', 'common').title()
    power = waifu.get('power', 0)
    
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }
    rarity_emoji = rarity_emojis.get(waifu.get('rarity', 'common'), "⚪")
    
    # Activity headers
    activity_headers = {
        "legendary": [
            "🔥 **LEGENDARY BADDIE ALERT!**",
            "💎 **ULTRA RARE SPAWN!**",
            "👑 **A QUEEN HAS ARRIVED!**",
            "⚡ **MAXIMUM ACTIVITY REWARD!**"
        ],
        "epic": [
            "✨ **EPIC BADDIE SPOTTED!**",
            "🌟 **HIGH TIER WAIFU APPEARED!**",
            "💫 **RARE CATCH OPPORTUNITY!**",
            "🔥 **HOT SPAWN ALERT!**"
        ],
        "rare": [
            "💎 **A CUTIE APPEARED!**",
            "✨ **SOMEONE'S LOOKING AT YOU!**",
            "🌸 **NEW CHALLENGER!**",
            "💕 **BADDIE IN THE BUILDING!**"
        ],
        "common": [
            "👀 **A WILD BADDIE APPEARED!**",
            "💋 **LOOK WHO SHOWED UP!**",
            "😏 **SHE'S WAITING FOR YOU...**",
            "🎯 **TARGET ACQUIRED!**"
        ]
    }
    
    header = random.choice(activity_headers.get(activity_level, activity_headers["common"]))
    
    # Flirty descriptions
    flirt_lines = [
        f"**{name}** is looking for someone brave enough... 👀",
        f"**{name}** wants to know if you got rizz 😏",
        f"Do you have what it takes to catch **{name}**? 🔥",
        f"**{name}** is judging your vibe rn... 💅",
        f"She's kinda bad tho... will you shoot your shot? 💘",
        f"**{name}** appeared! Make your move! ⚡",
        f"First one to smash gets a chance with **{name}**! 🎯",
        f"**{name}** is waiting... don't be shy! 💋"
    ]
    
    return f"""
{header}

{rarity_emoji} **{name}**

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📺 **Anime:** {anime}
┃ 💎 **Rarity:** {rarity}
┃ ⚔️ **Power:** {power}
┃ 🎯 **Catch Rate:** {win_chance}%
┗━━━━━━━━━━━━━━━━━━━━━━┛

{random.choice(flirt_lines)}

⚡ **First click = First try!**
⚠️ No guarantee - she might reject you!
⏰ _Disappears in 40 seconds..._
"""


def get_catching_caption(waifu_name: str, user_name: str) -> str:
    """Get sexy catching animation caption"""
    
    captions = [
        f"💥 **{user_name}** is shooting their shot...\n\n"
        f"Making moves on **{waifu_name}**... 😏🔥",
        
        f"🔥 **{user_name}** slides into position...\n\n"
        f"Going for **{waifu_name}**... 💋",
        
        f"💋 **{user_name}** activates rizz mode...\n\n"
        f"Charming **{waifu_name}**... ✨",
        
        f"😈 **{user_name}** makes their move...\n\n"
        f"Will **{waifu_name}** accept? 💕",
        
        f"⚡ **{user_name}** goes for it...\n\n"
        f"**{waifu_name}** is deciding... 🎲",
    ]
    return random.choice(captions)


def get_win_spawn_caption(waifu: dict, user_name: str, coins: int, delete_time: int) -> str:
    """Get sexy win caption for spawn with auto-delete notice"""
    
    name = waifu.get('name', 'Unknown')
    anime = waifu.get('anime', 'Unknown')
    rarity = waifu.get('rarity', 'common').title()
    power = waifu.get('power', 0)
    
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }
    rarity_emoji = rarity_emojis.get(waifu.get('rarity', 'common'), "⚪")
    
    win_headers = [
        f"🔥 **BADDIE SECURED!**",
        f"💋 **{user_name.upper()} GOT RIZZ!**",
        f"😈 **CAUGHT IN 4K!**",
        f"💕 **SHE SAID YES!**",
        f"🎉 **SMASH SUCCESSFUL!**",
        f"✨ **WHAT A CATCH!**",
        f"👑 **RIZZ GOD MOMENT!**",
        f"🏆 **CHAMPION MOVE!**"
    ]
    
    win_messages = [
        f"**{name}** fell for **{user_name}**'s charm! 😏",
        f"**{user_name}** really said \"she's mine\" and meant it! 💪",
        f"**{name}** is now down bad for **{user_name}**! 💘",
        f"**{user_name}** pulled **{name}** with that W rizz! 🔥",
        f"**{name}** couldn't resist **{user_name}**! ✨",
        f"**{user_name}** added **{name}** to the collection! 📦",
    ]
    
    return f"""
{random.choice(win_headers)}

{random.choice(win_messages)}

{rarity_emoji} **{name}**
┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📺 {anime}
┃ 💎 {rarity}
┃ ⚔️ Power: {power}
┃ 💰 +{coins} coins
┗━━━━━━━━━━━━━━━━━━━━━━┛

GG **{user_name}**! Check /collection 🎊

🗑️ _Auto-deleting in {delete_time}s..._
"""


def get_lose_spawn_caption(waifu: dict, user_name: str, win_chance: int, delete_time: int) -> str:
    """Get rejection caption for spawn WITH delete notice"""
    
    name = waifu.get('name', 'Unknown')
    anime = waifu.get('anime', 'Unknown')
    rarity = waifu.get('rarity', 'common').title()
    
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }
    rarity_emoji = rarity_emojis.get(waifu.get('rarity', 'common'), "⚪")
    
    lose_headers = [
        f"💔 **REJECTED HARD!**",
        f"💀 **{user_name.upper()} GOT CURVED!**",
        f"😭 **NO RIZZ DETECTED!**",
        f"🚫 **SHE SAID NOPE!**",
        f"😬 **FRIENDZONED!**",
        f"📉 **RIZZ FAILED!**",
        f"🥶 **COLD SHOULDER!**",
        f"💨 **SHE RAN AWAY!**"
    ]
    
    lose_messages = [
        f"**{name}** looked at **{user_name}** and said \"ew\" 💀",
        f"**{user_name}** tried but **{name}** wasn't having it 🙅‍♀️",
        f"**{name}** ghosted **{user_name}** in real time 👻",
        f"**{user_name}**'s rizz wasn't strong enough 📉",
        f"**{name}** said \"I have a boyfriend\" and left 🏃‍♀️",
        f"**{name}** pretended not to see **{user_name}** 👀",
        f"**{user_name}** got left on read IRL 📱",
    ]
    
    return f"""
{random.choice(lose_headers)}

{random.choice(lose_messages)}

{rarity_emoji} **{name}** escaped!

📺 Anime: {anime}
💎 Rarity: {rarity}
🎯 Catch Rate was: {win_chance}%

Better luck next time **{user_name}**! 😢
The grind continues... 💪

🗑️ _Auto-deleting in {delete_time}s..._
"""


def get_expired_caption(waifu: dict) -> str:
    """Get expired spawn caption"""
    
    name = waifu.get('name', 'Unknown')
    
    expired_msgs = [
        f"💨 **{name}** got bored and left...",
        f"⏰ **{name}** said \"y'all too slow\" and dipped",
        f"🏃‍♀️ **{name}** ran away! No one was brave enough...",
        f"😴 **{name}** fell asleep waiting for someone...",
        f"👋 **{name}** left the chat. Too many cowards here!",
        f"💅 **{name}** said \"not worth my time\" and vanished",
    ]
    
    return random.choice(expired_msgs)


# ═══════════════════════════════════════════════════════════════════
#  🗑️ AUTO-DELETE FUNCTION
# ═══════════════════════════════════════════════════════════════════

async def auto_delete_spawn_message(client: Client, chat_id: int, message_id: int, delay: int):
    """Delete spawn message after delay"""
    try:
        print(f"🗑️ [AUTO-DELETE] Will delete spawn in {delay}s")
        await asyncio.sleep(delay)
        
        await client.delete_messages(chat_id, message_id)
        print(f"✅ [AUTO-DELETE] Deleted spawn message in chat {chat_id}")
        
    except Exception as e:
        print(f"⚠️ [AUTO-DELETE] Could not delete spawn: {e}")


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def get_group_settings(chat_id: int) -> dict:
    if chat_id not in group_settings:
        group_settings[chat_id] = DEFAULT_SETTINGS.copy()
    return group_settings[chat_id]


def update_group_setting(chat_id: int, setting: str, value) -> bool:
    if chat_id not in group_settings:
        group_settings[chat_id] = DEFAULT_SETTINGS.copy()
    
    if setting in group_settings[chat_id]:
        group_settings[chat_id][setting] = value
        return True
    return False


async def is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


def get_rarity_by_activity(message_count: int) -> str:
    if message_count >= RARITY_THRESHOLDS["legendary"]:
        weights = {"legendary": 20, "epic": 30, "rare": 30, "common": 20}
    elif message_count >= RARITY_THRESHOLDS["epic"]:
        weights = {"legendary": 10, "epic": 25, "rare": 35, "common": 30}
    elif message_count >= RARITY_THRESHOLDS["rare"]:
        weights = {"legendary": 2, "epic": 13, "rare": 35, "common": 50}
    else:
        weights = {"legendary": 0, "epic": 5, "rare": 20, "common": 75}
    
    rarities = list(weights.keys())
    weight_values = list(weights.values())
    return random.choices(rarities, weights=weight_values, k=1)[0]


def get_activity_level(message_count: int) -> str:
    """Get activity level string"""
    if message_count >= RARITY_THRESHOLDS["legendary"]:
        return "legendary"
    elif message_count >= RARITY_THRESHOLDS["epic"]:
        return "epic"
    elif message_count >= RARITY_THRESHOLDS["rare"]:
        return "rare"
    return "common"


def calculate_win(win_chance: int) -> bool:
    return random.randint(1, 100) <= win_chance


def should_spawn(chat_id: int) -> tuple:
    settings = get_group_settings(chat_id)
    
    if not settings.get("enabled", True):
        return False, "disabled"
    
    if chat_id not in group_activity:
        return False, "no_activity"
    
    data = group_activity[chat_id]
    
    if len(data["users"]) < settings["min_users"]:
        return False, "not_enough_users"
    
    time_since_spawn = time.time() - data.get("last_spawn", 0)
    if time_since_spawn < settings["cooldown"]:
        return False, "cooldown"
    
    if chat_id in active_spawns:
        return False, "already_active"
    
    message_count = data["messages"]
    
    if message_count >= settings["max_messages"]:
        return True, "max_messages"
    
    if message_count >= settings["min_messages"]:
        base_chance = 5
        extra_chance = (message_count - settings["min_messages"]) * 3
        spawn_chance = min(base_chance + extra_chance, 80)
        
        if random.randint(1, 100) <= spawn_chance:
            return True, "random"
    
    return False, "not_enough_messages"


def get_waifu_by_rarity(wm, target_rarity: str):
    try:
        all_waifus = wm.waifus if hasattr(wm, 'waifus') else []
        matching = [w for w in all_waifus if w.get("rarity", "common") == target_rarity]
        
        if matching:
            return random.choice(matching)
        return wm.get_random_waifu()
    except:
        return wm.get_random_waifu()


# ═══════════════════════════════════════════════════════════════════
#  Admin Commands
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["setspawn", "spawnset"]) & filters.group)
async def set_spawn_command(client: Client, message: Message):
    user = message.from_user
    chat_id = message.chat.id
    
    is_admin = await is_group_admin(client, chat_id, user.id)
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if not is_admin and user.id != owner_id:
        await message.reply_text("❌ Only admins can change this!")
        return
    
    args = message.text.split()[1:]
    
    if len(args) < 2:
        await message.reply_text(
            "**⚙️ Spawn Settings**\n\n"
            "**Usage:** `/setspawn <setting> <value>`\n\n"
            "**Settings:**\n"
            "• `messages` - Min messages (5-100)\n"
            "• `maxmessages` - Force spawn (20-200)\n"
            "• `cooldown` - Seconds between spawns (30-600)\n"
            "• `users` - Min unique users (1-10)\n"
            "• `autodelete` - Delete time after smash (5-60)\n\n"
            "**Example:** `/setspawn autodelete 10`"
        )
        return
    
    setting = args[0].lower()
    
    try:
        value = int(args[1])
    except ValueError:
        await message.reply_text("❌ Value must be a number!")
        return
    
    setting_map = {
        "messages": "min_messages",
        "minmessages": "min_messages",
        "maxmessages": "max_messages",
        "cooldown": "cooldown",
        "users": "min_users",
        "minusers": "min_users",
        "autodelete": "auto_delete_after_smash",
        "delete": "auto_delete_after_smash"
    }
    
    actual_setting = setting_map.get(setting)
    
    if not actual_setting:
        await message.reply_text(f"❌ Unknown setting: `{setting}`")
        return
    
    min_val, max_val = SETTING_LIMITS.get(actual_setting, (0, 999))
    
    if value < min_val or value > max_val:
        await message.reply_text(f"❌ Value must be between {min_val} and {max_val}!")
        return
    
    update_group_setting(chat_id, actual_setting, value)
    
    await message.reply_text(f"✅ **{actual_setting}** set to `{value}`!")


@Client.on_message(filters.command(["spawnsettings", "spawnconfig"]) & filters.group)
async def spawn_settings_command(client: Client, message: Message):
    chat_id = message.chat.id
    settings = get_group_settings(chat_id)
    
    status = "✅ Enabled" if settings["enabled"] else "❌ Disabled"
    
    text = f"""
⚙️ **Spawn Settings**

**Status:** {status}

📊 **Requirements:**
• Min Messages: `{settings['min_messages']}`
• Max Messages: `{settings['max_messages']}`
• Min Users: `{settings['min_users']}`

⏰ **Timings:**
• Cooldown: `{settings['cooldown']}s`
• Expiry: `40s`
• Auto-delete after smash: `{settings.get('auto_delete_after_smash', 10)}s`

🎯 **Win Chances:**
• Common: `{WIN_CHANCES['common']}%`
• Rare: `{WIN_CHANCES['rare']}%`
• Epic: `{WIN_CHANCES['epic']}%`
• Legendary: `{WIN_CHANCES['legendary']}%`

⚡ First come, first serve!
🗑️ ALL smashed waifus auto-delete after {settings.get('auto_delete_after_smash', 10)}s
"""
    
    await message.reply_text(text)


@Client.on_message(filters.command(["togglespawn", "spawntoggle"]) & filters.group)
async def toggle_spawn_command(client: Client, message: Message):
    user = message.from_user
    chat_id = message.chat.id
    
    is_admin = await is_group_admin(client, chat_id, user.id)
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if not is_admin and user.id != owner_id:
        await message.reply_text("❌ Only admins can toggle spawn!")
        return
    
    settings = get_group_settings(chat_id)
    new_status = not settings.get("enabled", True)
    update_group_setting(chat_id, "enabled", new_status)
    
    if new_status:
        await message.reply_text("✅ **Auto Spawn Enabled!** 🔥")
    else:
        await message.reply_text("❌ **Auto Spawn Disabled!**")


# ═══════════════════════════════════════════════════════════════════
#  Message Tracker
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.group & ~filters.bot & ~filters.service, group=5)
async def track_group_messages(client: Client, message: Message):
    if not message.from_user:
        return
    
    # Skip commands
    if message.text and message.text.startswith(("/", "!", ".")):
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    settings = get_group_settings(chat_id)
    if not settings.get("enabled", True):
        return
    
    if chat_id not in group_activity:
        group_activity[chat_id] = {
            "messages": 0,
            "users": set(),
            "last_spawn": 0
        }
    
    group_activity[chat_id]["messages"] += 1
    group_activity[chat_id]["users"].add(user_id)
    
    spawn, reason = should_spawn(chat_id)
    
    if spawn:
        print(f"🎲 [AUTO-SPAWN] Spawning! Reason: {reason}")
        await spawn_waifu_in_group(client, message.chat)


# ═══════════════════════════════════════════════════════════════════
#  Spawn Function
# ═══════════════════════════════════════════════════════════════════

async def spawn_waifu_in_group(client: Client, chat):
    chat_id = chat.id
    chat_title = getattr(chat, 'title', 'Unknown Group')
    message_count = group_activity.get(chat_id, {}).get("messages", 0)
    
    print(f"🎲 [AUTO-SPAWN] Spawning in '{chat_title}' ({chat_id})")
    
    try:
        wm = get_waifu_manager()
    except Exception as e:
        print(f"❌ [AUTO-SPAWN] WaifuManager error: {e}")
        return
    
    target_rarity = get_rarity_by_activity(message_count)
    waifu = get_waifu_by_rarity(wm, target_rarity)
    
    if not waifu:
        waifu = wm.get_random_waifu()
    
    if not waifu:
        print(f"❌ [AUTO-SPAWN] No waifu available!")
        return
    
    rarity = waifu.get("rarity", "common")
    win_chance = WIN_CHANCES.get(rarity, 50)
    activity_level = get_activity_level(message_count)
    
    # Create unique spawn ID using timestamp
    spawn_time = int(time.time())
    
    # Store spawn data - use simple structure
    active_spawns[chat_id] = {
        "waifu": waifu,
        "waifu_id": waifu.get("id"),
        "spawned_at": spawn_time,
        "message_id": None,
        "claimed_by": None,  # Track who clicked
        "processed": False   # Track if already processed
    }
    
    # Reset activity
    group_activity[chat_id] = {
        "messages": 0,
        "users": set(),
        "last_spawn": time.time()
    }
    
    # Get sexy caption
    text = get_spawn_caption(waifu, activity_level, win_chance)
    
    # Simple callback data - just chat_id and waifu_id
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💥 SMASH HER!", 
                callback_data=f"gsmash:{chat_id}:{waifu.get('id')}"
            )
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    try:
        if image_url:
            sent_msg = await client.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=text,
                reply_markup=buttons
            )
        else:
            sent_msg = await client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=buttons
            )
        
        active_spawns[chat_id]["message_id"] = sent_msg.id
        
        print(f"✅ [AUTO-SPAWN] Spawned: {waifu.get('name')} ({rarity}) - {win_chance}%")
        
        # 40 second expiry
        asyncio.create_task(check_spawn_expiry(client, chat_id, spawn_time))
        
    except Exception as e:
        print(f"❌ [AUTO-SPAWN] Send error: {e}")
        if chat_id in active_spawns:
            del active_spawns[chat_id]


# ═══════════════════════════════════════════════════════════════════
#  Expiry Handler
# ═══════════════════════════════════════════════════════════════════

async def check_spawn_expiry(client: Client, chat_id: int, spawn_time: int):
    """Check and handle spawn expiry after 40 seconds"""
    await asyncio.sleep(40)
    
    # Check if spawn still exists and wasn't claimed
    if chat_id not in active_spawns:
        return
    
    spawn_data = active_spawns.get(chat_id, {})
    
    # Check if it's the same spawn (using spawn time)
    if spawn_data.get("spawned_at") != spawn_time:
        return
    
    # Check if already processed
    if spawn_data.get("processed", False):
        return
    
    waifu = spawn_data.get("waifu", {})
    message_id = spawn_data.get("message_id")
    
    # Clean up
    del active_spawns[chat_id]
    
    print(f"⏰ [AUTO-SPAWN] Expired: {waifu.get('name')} in {chat_id}")
    
    # Try to edit message with expired text, then delete
    try:
        expired_text = get_expired_caption(waifu)
        
        await client.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=expired_text,
            reply_markup=None
        )
        
        # Delete after 3 seconds
        await asyncio.sleep(3)
        await client.delete_messages(chat_id, message_id)
        
    except Exception as e:
        print(f"⚠️ [AUTO-SPAWN] Expiry handling error: {e}")
        try:
            await client.delete_messages(chat_id, message_id)
        except:
            pass


# ═══════════════════════════════════════════════════════════════════
#  🔥 CATCH CALLBACK - AUTO-DELETE ON BOTH WIN AND LOSE
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^gsmash:"))
async def group_catch_callback(client: Client, callback: CallbackQuery):
    """Handle group catch - Auto-delete regardless of result"""
    
    print(f"💥 [GSMASH] Callback received: {callback.data}")
    
    try:
        # Parse callback data: gsmash:chat_id:waifu_id
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Invalid data!", show_alert=True)
            return
        
        chat_id = int(parts[1])
        waifu_id = int(parts[2])
        
    except (ValueError, IndexError) as e:
        print(f"❌ [GSMASH] Parse error: {e}")
        await callback.answer("❌ Error processing!", show_alert=True)
        return
    
    user = callback.from_user
    
    print(f"🎯 [GSMASH] User {user.first_name} trying for waifu {waifu_id} in chat {chat_id}")
    
    # Check if spawn still active
    if chat_id not in active_spawns:
        await callback.answer(
            "❌ Too late! This baddie already left! 💨", 
            show_alert=True
        )
        return
    
    spawn_data = active_spawns[chat_id]
    
    # Verify waifu ID matches
    if spawn_data.get("waifu_id") != waifu_id:
        await callback.answer("❌ Wrong waifu! Try again!", show_alert=True)
        return
    
    # Check if already claimed by someone
    if spawn_data.get("claimed_by") is not None:
        await callback.answer(
            "❌ Someone already clicked! Wait for next spawn! 😤", 
            show_alert=True
        )
        return
    
    # Check if already processed
    if spawn_data.get("processed", False):
        await callback.answer(
            "❌ This spawn already ended!", 
            show_alert=True
        )
        return
    
    # CLAIM IT! Mark as claimed
    spawn_data["claimed_by"] = user.id
    spawn_data["processed"] = True
    
    waifu = spawn_data["waifu"]
    
    print(f"✅ [GSMASH] Claimed by {user.first_name}!")
    
    # Get waifu manager for rarity emoji
    try:
        wm = get_waifu_manager()
    except:
        wm = None
    
    rarity = waifu.get("rarity", "common")
    win_chance = WIN_CHANCES.get(rarity, 50)
    
    # Get auto-delete setting
    settings = get_group_settings(chat_id)
    delete_time = settings.get("auto_delete_after_smash", 10)
    
    # Show catching animation
    catching_text = get_catching_caption(waifu.get('name', 'Unknown'), user.first_name)
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=catching_text, reply_markup=None)
        else:
            await callback.message.edit_text(text=catching_text, reply_markup=None)
    except Exception as e:
        print(f"⚠️ [GSMASH] Edit error: {e}")
    
    # Quick answer to show progress
    await callback.answer("💥 Shooting your shot... 😏", show_alert=False)
    
    # Dramatic pause
    await asyncio.sleep(2)
    
    # Calculate win/lose
    is_win = calculate_win(win_chance)
    
    print(f"🎲 [GSMASH] {user.first_name} - {win_chance}% chance - {'WIN' if is_win else 'LOSE'}")
    
    # Remove from active spawns
    if chat_id in active_spawns:
        del active_spawns[chat_id]
    
    if is_win:
        # ═══════════════════════════════════════════
        #  USER WINS! 🎉
        # ═══════════════════════════════════════════
        
        # Database operations
        try:
            db.get_or_create_user(user.id, user.username, user.first_name)
        except Exception as e:
            print(f"⚠️ [GSMASH] User create error: {e}")
        
        try:
            db.add_waifu_to_collection(user.id, waifu)
            print(f"✅ [GSMASH] Added {waifu.get('name')} to {user.first_name}'s collection")
        except Exception as e:
            print(f"⚠️ [GSMASH] Collection error: {e}")
        
        # Coins based on rarity
        coins_reward = {
            "common": 15,
            "rare": 50,
            "epic": 100,
            "legendary": 200
        }.get(rarity, 15)
        
        try:
            db.add_coins(user.id, coins_reward)
        except Exception as e:
            print(f"⚠️ [GSMASH] Coins error: {e}")
        
        try:
            db.increment_user_stats(user.id, "total_wins")
            db.increment_user_stats(user.id, "total_smash")
        except Exception as e:
            print(f"⚠️ [GSMASH] Stats error: {e}")
        
        # Get sexy win caption WITH delete notice
        text = get_win_spawn_caption(waifu, user.first_name, coins_reward, delete_time)
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            else:
                await callback.message.edit_text(text=text, reply_markup=None)
        except Exception as e:
            print(f"⚠️ [GSMASH] Final edit error: {e}")
        
        # Victory popup
        win_popups = [
            f"🔥 SHE'S YOURS! {waifu.get('name')} is down bad!",
            f"💋 CAUGHT! {waifu.get('name')} joined your harem!",
            f"😈 W RIZZ! +{coins_reward} coins!",
            f"✨ BADDIE SECURED! GG!",
        ]
        await callback.answer(random.choice(win_popups), show_alert=True)
        
    else:
        # ═══════════════════════════════════════════
        #  USER LOSES! 💔
        # ═══════════════════════════════════════════
        
        try:
            db.get_or_create_user(user.id, user.username, user.first_name)
            db.increment_user_stats(user.id, "total_losses")
        except Exception as e:
            print(f"⚠️ [GSMASH] Loss stats error: {e}")
        
        # Get rejection caption WITH delete notice
        text = get_lose_spawn_caption(waifu, user.first_name, win_chance, delete_time)
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            else:
                await callback.message.edit_text(text=text, reply_markup=None)
        except Exception as e:
            print(f"⚠️ [GSMASH] Final edit error: {e}")
        
        # Rejection popups
        lose_popups = [
            f"💔 REJECTED! {waifu.get('name')} said no!",
            f"💀 NO RIZZ! She curved you hard!",
            f"😭 L + Ratio! Better luck next time!",
            f"🚫 She said EW and left!",
            f"📉 Your rizz wasn't enough today!",
        ]
        await callback.answer(random.choice(lose_popups), show_alert=True)
    
    # 🗑️ ALWAYS SCHEDULE AUTO-DELETE (WIN OR LOSE)
    asyncio.create_task(
        auto_delete_spawn_message(
            client, 
            chat_id, 
            callback.message.id, 
            delete_time
        )
    )
    
    print(f"🗑️ [GSMASH] Scheduled auto-delete in {delete_time}s (Result: {'WIN' if is_win else 'LOSE'})")


# ═══════════════════════════════════════════════════════════════════
#  Force Spawn & Stats
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["forcespawn", "fspawn"]) & filters.group)
async def force_spawn_command(client: Client, message: Message):
    user = message.from_user
    chat_id = message.chat.id
    
    is_admin = await is_group_admin(client, chat_id, user.id)
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if not is_admin and user.id != owner_id:
        await message.reply_text("❌ Only admins can force spawn!")
        return
    
    if chat_id in active_spawns:
        await message.reply_text("⚠️ A baddie is already active! Wait for her to leave!")
        return
    
    # Initialize activity if needed
    if chat_id not in group_activity:
        group_activity[chat_id] = {
            "messages": 50,  # Give good activity for force spawn
            "users": set(),
            "last_spawn": 0
        }
    
    await spawn_waifu_in_group(client, message.chat)
    
    try:
        await message.delete()
    except:
        pass


@Client.on_message(filters.command(["spawnstats", "sstats"]) & filters.group)
async def spawn_stats_command(client: Client, message: Message):
    chat_id = message.chat.id
    data = group_activity.get(chat_id, {})
    settings = get_group_settings(chat_id)
    
    msg_count = data.get("messages", 0)
    user_count = len(data.get("users", set()))
    last_spawn = data.get("last_spawn", 0)
    
    if last_spawn > 0:
        time_ago = int(time.time() - last_spawn)
        last_spawn_text = Utils.format_time(time_ago) + " ago"
    else:
        last_spawn_text = "Never"
    
    if msg_count >= settings["min_messages"]:
        base_chance = 5
        extra_chance = (msg_count - settings["min_messages"]) * 3
        spawn_chance = min(base_chance + extra_chance, 80)
    else:
        spawn_chance = 0
    
    activity_level = get_activity_level(msg_count)
    
    # Active spawn info
    active_info = ""
    if chat_id in active_spawns:
        spawn = active_spawns[chat_id]
        waifu = spawn.get("waifu", {})
        claimed = spawn.get("claimed_by")
        status = "❌ Claimed" if claimed else "✅ Available"
        active_info = f"\n\n🎯 **Active Spawn:**\n• {waifu.get('name')} ({waifu.get('rarity')})\n• Status: {status}"
    
    text = f"""
📊 **Spawn Stats**

💬 Messages: `{msg_count}/{settings['max_messages']}`
👥 Users: `{user_count}/{settings['min_users']}`
⏰ Last Spawn: `{last_spawn_text}`
🎯 Spawn Chance: `{spawn_chance}%`
🔥 Activity: `{activity_level.title()}`
🗑️ Auto-delete: `{settings.get('auto_delete_after_smash', 10)}s` after ANY smash{active_info}

⚡ Keep chatting for more spawns!
"""
    
    await message.reply_text(text)


@Client.on_message(filters.command(["resetspawn"]) & filters.group)
async def reset_spawn_command(client: Client, message: Message):
    user = message.from_user
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    is_admin = await is_group_admin(client, message.chat.id, user.id)
    
    if not is_admin and user.id != owner_id:
        return
    
    chat_id = message.chat.id
    
    if chat_id in group_activity:
        del group_activity[chat_id]
    
    if chat_id in active_spawns:
        del active_spawns[chat_id]
    
    await message.reply_text("✅ Spawn data reset! Fresh start! 🔥")
