# modules/auto_spawn.py - Auto Spawn System with Single Attempt

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

Waifus automatically spawn in group chats based on activity!

**How it works:**
• Waifus spawn based on chat activity
• First person to click SMASH gets to try
• You either WIN or LOSE - no second chances!
• Rarer waifus are harder to catch
• Spawns expire in 40 seconds

**Admin Commands:**
/setspawn <setting> <value> - Change spawn settings
/spawnsettings - View current settings
/togglespawn - Enable/Disable auto spawn
/forcespawn - Force spawn a waifu
"""

# ═══════════════════════════════════════════════════════════════════
#  Default Configuration
# ═══════════════════════════════════════════════════════════════════

DEFAULT_SETTINGS = {
    "enabled": True,
    "min_messages": 10,
    "max_messages": 50,
    "min_users": 2,
    "cooldown": 120,
    "expiry": 40  # Fixed 40 seconds expiry
}

SETTING_LIMITS = {
    "min_messages": (5, 100),
    "max_messages": (20, 200),
    "min_users": (1, 10),
    "cooldown": (30, 600)
}

RARITY_THRESHOLDS = {
    "legendary": 80,
    "epic": 50,
    "rare": 25,
    "common": 0
}

# Win chances by rarity (lower = harder to catch)
WIN_CHANCES = {
    "common": 70,
    "epic": 55,
    "legendary": 40,
    "rare": 25
}

# ═══════════════════════════════════════════════════════════════════
#  Data Storage
# ═══════════════════════════════════════════════════════════════════

group_settings = {}
group_activity = {}
active_spawns = {}

# Track who already tried (to prevent multiple attempts)
# {chat_id: {spawn_id: user_id}}
spawn_claims = {}


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


def calculate_win(win_chance: int) -> bool:
    """Calculate if user wins based on percentage"""
    return random.randint(1, 100) <= win_chance


def should_spawn(chat_id: int) -> tuple[bool, str]:
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
        await message.reply_text("❌ Only admins can change spawn settings!")
        return
    
    args = message.text.split()[1:]
    
    if len(args) < 2:
        await message.reply_text(
            "**Usage:** `/setspawn <setting> <value>`\n\n"
            "**Settings:**\n"
            "• `messages` - Min messages (5-100)\n"
            "• `maxmessages` - Force spawn (20-200)\n"
            "• `cooldown` - Seconds between spawns (30-600)\n"
            "• `users` - Min unique users (1-10)\n\n"
            "**Example:** `/setspawn cooldown 60`\n\n"
            "⚠️ **Note:** Expiry is fixed at 40 seconds"
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
        "minusers": "min_users"
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
    
    display_names = {
        "min_messages": "Minimum Messages",
        "max_messages": "Maximum Messages",
        "cooldown": "Spawn Cooldown",
        "min_users": "Minimum Users"
    }
    
    await message.reply_text(
        f"✅ **Setting Updated!**\n\n"
        f"**{display_names.get(actual_setting)}:** `{value}`"
    )


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
• Expiry: `40s` (Fixed)

🎯 **Win Chances:**
• Common: `{WIN_CHANCES['common']}%`
• Rare: `{WIN_CHANCES['rare']}%`
• Epic: `{WIN_CHANCES['epic']}%`
• Legendary: `{WIN_CHANCES['legendary']}%`

⚡ **First come, first serve!**
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
        await message.reply_text("✅ **Auto Spawn Enabled!**")
    else:
        await message.reply_text("❌ **Auto Spawn Disabled!**")


# ═══════════════════════════════════════════════════════════════════
#  Message Tracker
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.group & ~filters.bot & ~filters.service & ~filters.command(["smash", "waifu", "sp"]), group=5)
async def track_group_messages(client: Client, message: Message):
    if not message.from_user:
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
    
    msg_count = group_activity[chat_id]["messages"]
    if msg_count % 10 == 0:
        user_count = len(group_activity[chat_id]["users"])
        print(f"📊 [AUTO-SPAWN] Chat {chat_id}: {msg_count} msgs, {user_count} users")
    
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
    
    # Generate unique spawn ID
    spawn_id = f"{chat_id}_{int(time.time())}"
    
    # Store spawn data
    active_spawns[chat_id] = {
        "spawn_id": spawn_id,
        "waifu": waifu,
        "spawned_at": time.time(),
        "message_count": message_count,
        "message_id": None,
        "claimed": False
    }
    
    # Initialize spawn claim tracker
    if chat_id not in spawn_claims:
        spawn_claims[chat_id] = {}
    spawn_claims[chat_id][spawn_id] = None  # No one claimed yet
    
    # Reset activity
    group_activity[chat_id] = {
        "messages": 0,
        "users": set(),
        "last_spawn": time.time()
    }
    
    rarity_emoji = wm.get_rarity_emoji(rarity)
    
    if message_count >= RARITY_THRESHOLDS["legendary"]:
        activity_msg = "🔥 **LEGENDARY ACTIVITY!**"
    elif message_count >= RARITY_THRESHOLDS["epic"]:
        activity_msg = "⚡ **HIGH ACTIVITY!**"
    elif message_count >= RARITY_THRESHOLDS["rare"]:
        activity_msg = "✨ **GOOD ACTIVITY!**"
    else:
        activity_msg = "💫 **A wild waifu appeared!**"
    
    text = f"""
{activity_msg}

{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {rarity.title()}
⚔️ **Power:** {waifu.get('power', 0)}
🎯 **Catch Rate:** {win_chance}%

⚡ **First to click SMASH gets to try!**
⚠️ Not guaranteed - you might get rejected!
⏰ Expires in 40 seconds!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💥 SMASH!", 
                callback_data=f"gcatch_{chat_id}_{waifu['id']}_{spawn_id}"
            )
        ]
    ])
    
    image_url = waifu.get("image")
    
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
        
        print(f"✅ [AUTO-SPAWN] Spawned: {waifu.get('name')} ({rarity}) - {win_chance}% catch rate")
        
        # Fixed 40 second expiry
        asyncio.create_task(
            check_spawn_expiry(client, chat_id, sent_msg.id, spawn_id, 40)
        )
        
    except Exception as e:
        print(f"❌ [AUTO-SPAWN] Send error: {e}")
        if chat_id in active_spawns:
            del active_spawns[chat_id]


# ═══════════════════════════════════════════════════════════════════
#  Expiry Handler - Delete after 40 seconds
# ═══════════════════════════════════════════════════════════════════

async def check_spawn_expiry(client: Client, chat_id: int, message_id: int, spawn_id: str, expiry_time: int):
    await asyncio.sleep(expiry_time)
    
    if chat_id not in active_spawns:
        return
    
    spawn_data = active_spawns.get(chat_id, {})
    
    # Check if it's the same spawn
    if spawn_data.get("spawn_id") != spawn_id:
        return
    
    # Check if already claimed
    if spawn_data.get("claimed", False):
        return
    
    waifu = spawn_data.get("waifu", {})
    
    # Clean up
    del active_spawns[chat_id]
    
    if chat_id in spawn_claims and spawn_id in spawn_claims[chat_id]:
        del spawn_claims[chat_id][spawn_id]
    
    print(f"⏰ [AUTO-SPAWN] Expired: {waifu.get('name')} in {chat_id}")
    
    # Delete the message
    try:
        await client.delete_messages(chat_id, message_id)
        print(f"🗑️ [AUTO-SPAWN] Deleted expired spawn message")
    except Exception as e:
        print(f"⚠️ [AUTO-SPAWN] Could not delete message: {e}")


# ═══════════════════════════════════════════════════════════════════
#  Catch Callback - Single Attempt Only
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^gcatch_(-?\d+)_(\d+)_(.+)$"))
async def group_catch_callback(client: Client, callback: CallbackQuery):
    """Handle group catch - ONE attempt only!"""
    
    data = callback.data.split("_")
    chat_id = int(data[1])
    waifu_id = int(data[2])
    spawn_id = data[3]
    
    user = callback.from_user
    
    # Check if spawn still active
    if chat_id not in active_spawns:
        await callback.answer(
            "❌ Too late! This waifu is gone!", 
            show_alert=True
        )
        return
    
    spawn_data = active_spawns[chat_id]
    
    # Verify spawn ID
    if spawn_data.get("spawn_id") != spawn_id:
        await callback.answer("❌ Invalid spawn!", show_alert=True)
        return
    
    waifu = spawn_data["waifu"]
    
    if waifu.get("id") != waifu_id:
        await callback.answer("❌ Invalid waifu!", show_alert=True)
        return
    
    # Check if already claimed
    if spawn_data.get("claimed", False):
        await callback.answer(
            "❌ Too late! Someone already tried!", 
            show_alert=True
        )
        return
    
    # Check if someone already clicked
    if chat_id in spawn_claims and spawn_id in spawn_claims[chat_id]:
        if spawn_claims[chat_id][spawn_id] is not None:
            await callback.answer(
                "❌ Someone already clicked! Wait for next spawn!", 
                show_alert=True
            )
            return
    
    # Mark as claimed by this user
    spawn_data["claimed"] = True
    spawn_claims[chat_id][spawn_id] = user.id
    
    wm = get_waifu_manager()
    rarity = waifu.get("rarity", "common")
    win_chance = WIN_CHANCES.get(rarity, 50)
    
    # Calculate win/lose
    is_win = calculate_win(win_chance)
    
    print(f"🎲 [GCATCH] {user.first_name} tried for {waifu.get('name')} - {win_chance}% - {'WIN' if is_win else 'LOSE'}")
    
    # Remove from active spawns
    del active_spawns[chat_id]
    
    if is_win:
        # ═══════════════════════════════════════════
        #  USER WINS!
        # ═══════════════════════════════════════════
        
        # Add to database
        try:
            db.get_or_create_user(user.id, user.username, user.first_name)
        except:
            pass
        
        try:
            db.add_waifu_to_collection(user.id, waifu)
        except:
            pass
        
        coins_reward = {
            "common": 15,
            "rare": 35,
            "epic": 75,
            "legendary": 150
        }.get(rarity, 15)
        
        try:
            db.add_coins(user.id, coins_reward)
        except:
            pass
        
        try:
            db.increment_user_stats(user.id, "total_wins")
            db.increment_user_stats(user.id, "total_smash")
        except:
            pass
        
        rarity_emoji = wm.get_rarity_emoji(rarity)
        
        text = f"""
🎉 **CAUGHT!**

{rarity_emoji} **{waifu.get('name')}** was caught by **{user.first_name}**! 🏆

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
⚔️ Power: {waifu.get('power')}
💰 Coins: +{coins_reward}

Congratulations! 🎊
"""
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            else:
                await callback.message.edit_text(text=text, reply_markup=None)
        except:
            pass
        
        await callback.answer(
            f"🎉 You caught {waifu.get('name')}! +{coins_reward} coins", 
            show_alert=True
        )
        
    else:
        # ═══════════════════════════════════════════
        #  USER LOSES - No more attempts!
        # ═══════════════════════════════════════════
        
        # Update stats
        try:
            db.get_or_create_user(user.id, user.username, user.first_name)
            db.increment_user_stats(user.id, "total_losses")
        except:
            pass
        
        rarity_emoji = wm.get_rarity_emoji(rarity)
        
        text = f"""
💔 **REJECTED!**

{user.first_name} tried to catch **{waifu.get('name')}** but got rejected!

{rarity_emoji} **{waifu.get('name')}** escaped!

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
🎯 Catch Rate was: {win_chance}%

Better luck next time! 😢
"""
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            else:
                await callback.message.edit_text(text=text, reply_markup=None)
        except:
            pass
        
        # Random rejection messages
        rejection_msgs = [
            f"💔 {waifu.get('name')} rejected you!",
            f"😢 Not this time! {waifu.get('name')} escaped!",
            f"❌ So close! But {waifu.get('name')} got away!",
            f"💨 {waifu.get('name')} dodged and ran away!",
            f"😅 Better luck next time!",
            f"🏃 {waifu.get('name')} said no and left!"
        ]
        
        await callback.answer(
            random.choice(rejection_msgs), 
            show_alert=True
        )
    
    # Clean up spawn claims
    if chat_id in spawn_claims and spawn_id in spawn_claims[chat_id]:
        del spawn_claims[chat_id][spawn_id]


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
        await message.reply_text("❌ Only admins can use this command!")
        return
    
    if chat_id in active_spawns:
        await message.reply_text("⚠️ A waifu is already active! Wait for it to expire!")
        return
    
    await spawn_waifu_in_group(client, message.chat)


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
    
    predicted_rarity = get_rarity_by_activity(msg_count)
    
    # Check if there's active spawn
    active_info = ""
    if chat_id in active_spawns:
        spawn = active_spawns[chat_id]
        waifu = spawn.get("waifu", {})
        claimed = "❌ Already claimed" if spawn.get("claimed") else "✅ Available"
        active_info = f"\n\n🎯 **Active Spawn:**\n• {waifu.get('name')} ({waifu.get('rarity')})\n• Status: {claimed}"
    
    text = f"""
📊 **Spawn Statistics**

💬 Messages: {msg_count}/{settings['max_messages']}
👥 Unique Users: {user_count}/{settings['min_users']}
⏰ Last Spawn: {last_spawn_text}
🎯 Spawn Chance: {spawn_chance}%
💎 Likely Rarity: {predicted_rarity.title()}{active_info}

⚡ Remember: First click only!
"""
    
    await message.reply_text(text)


@Client.on_message(filters.command(["resetspawn"]) & filters.group)
async def reset_spawn_command(client: Client, message: Message):
    user = message.from_user
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if user.id != owner_id:
        return
    
    chat_id = message.chat.id
    
    if chat_id in group_activity:
        del group_activity[chat_id]
    
    if chat_id in active_spawns:
        del active_spawns[chat_id]
    
    if chat_id in spawn_claims:
        del spawn_claims[chat_id]
    
    await message.reply_text("✅ Spawn activity reset!")
