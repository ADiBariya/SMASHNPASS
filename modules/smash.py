# modules/smash.py - Main Game Module with Auto Spawn

import random
import asyncio
from datetime import datetime, timedelta
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
__MODULE__ = "Smash"
__HELP__ = """
🎮 **Smash Game**
/smash - Start a new game
/waifu - Same as smash
/sp - Short command

🌟 **Auto Spawn**
Waifus automatically spawn in groups based on chat activity!
Be the first to smash and claim them!
"""

# Store active games {user_id: waifu_data}
active_games = {}

# ═══════════════════════════════════════════════════════════════════
#  AUTO SPAWN SYSTEM
# ═══════════════════════════════════════════════════════════════════

# Auto spawn tracking per chat
# {chat_id: {"messages": set(user_ids), "count": int, "last_spawn": datetime, "last_waifu": dict}}
chat_spawn_data = {}

# Auto spawn settings
SPAWN_MESSAGE_MIN = 10          # Minimum messages for common spawn
SPAWN_MESSAGE_RARE = 25         # Messages for rare chance
SPAWN_MESSAGE_EPIC = 50         # Messages for epic chance
SPAWN_MESSAGE_LEGENDARY = 100   # Messages for legendary chance
SPAWN_COOLDOWN = 60             # Seconds between spawns in same chat
MIN_UNIQUE_USERS = 3            # Minimum unique users needed

# Active spawned waifus in chats {chat_id: {"waifu": dict, "message_id": int, "spawned_at": datetime}}
active_spawns = {}


def get_spawn_rarity(message_count: int) -> str:
    """Determine rarity based on message count"""
    if message_count >= SPAWN_MESSAGE_LEGENDARY:
        # High chance legendary, else epic
        roll = random.randint(1, 100)
        if roll <= 30:
            return "legendary"
        elif roll <= 60:
            return "epic"
        else:
            return "rare"
    elif message_count >= SPAWN_MESSAGE_EPIC:
        # Medium-high activity
        roll = random.randint(1, 100)
        if roll <= 15:
            return "legendary"
        elif roll <= 45:
            return "epic"
        else:
            return "rare"
    elif message_count >= SPAWN_MESSAGE_RARE:
        # Medium activity
        roll = random.randint(1, 100)
        if roll <= 5:
            return "epic"
        elif roll <= 35:
            return "rare"
        else:
            return "common"
    else:
        # Low activity = mostly common
        roll = random.randint(1, 100)
        if roll <= 10:
            return "rare"
        else:
            return "common"


def should_spawn(chat_id: int) -> tuple[bool, str]:
    """Check if waifu should spawn and return rarity"""
    if chat_id not in chat_spawn_data:
        return False, "common"
    
    data = chat_spawn_data[chat_id]
    unique_users = len(data.get("messages", set()))
    message_count = data.get("count", 0)
    last_spawn = data.get("last_spawn")
    
    # Check minimum unique users
    if unique_users < MIN_UNIQUE_USERS:
        return False, "common"
    
    # Check cooldown
    if last_spawn:
        cooldown_end = last_spawn + timedelta(seconds=SPAWN_COOLDOWN)
        if datetime.now() < cooldown_end:
            return False, "common"
    
    # Check minimum messages
    if message_count < SPAWN_MESSAGE_MIN:
        return False, "common"
    
    # Calculate spawn chance based on messages
    # More messages = higher spawn chance
    spawn_chance = min(50, 10 + (message_count // 5))  # Max 50% chance
    
    roll = random.randint(1, 100)
    if roll <= spawn_chance:
        rarity = get_spawn_rarity(message_count)
        return True, rarity
    
    return False, "common"


def reset_chat_counter(chat_id: int):
    """Reset chat message counter after spawn"""
    if chat_id in chat_spawn_data:
        chat_spawn_data[chat_id] = {
            "messages": set(),
            "count": 0,
            "last_spawn": datetime.now(),
            "last_waifu": chat_spawn_data[chat_id].get("last_waifu")
        }


# ═══════════════════════════════════════════════════════════════════
#  MESSAGE LISTENER FOR AUTO SPAWN
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.group & ~filters.bot & ~filters.command(["smash", "waifu", "sp"]))
async def message_listener(client: Client, message: Message):
    """Listen to group messages for auto spawn"""
    
    if not message.from_user:
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Initialize chat data if not exists
    if chat_id not in chat_spawn_data:
        chat_spawn_data[chat_id] = {
            "messages": set(),
            "count": 0,
            "last_spawn": None,
            "last_waifu": None
        }
    
    # Add user to unique users set and increment count
    chat_spawn_data[chat_id]["messages"].add(user_id)
    chat_spawn_data[chat_id]["count"] += 1
    
    # Check if should spawn
    should, rarity = should_spawn(chat_id)
    
    if should:
        await spawn_waifu(client, message.chat, rarity)


async def spawn_waifu(client: Client, chat, target_rarity: str):
    """Spawn a waifu in the chat"""
    
    chat_id = chat.id
    wm = get_waifu_manager()
    
    # Get waifu of specific rarity
    waifu = wm.get_waifu_by_rarity(target_rarity)
    
    if not waifu:
        # Fallback to random
        waifu = wm.get_random_waifu()
    
    if not waifu:
        return
    
    print(f"🌟 [AUTO-SPAWN] Spawning {waifu.get('name')} ({target_rarity}) in {chat.title}")
    
    # Reset counter
    reset_chat_counter(chat_id)
    
    # Store spawn data
    active_spawns[chat_id] = {
        "waifu": waifu,
        "spawned_at": datetime.now(),
        "claimed": False,
        "claimed_by": None
    }
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    rarity = waifu.get("rarity", "common").title()
    
    text = f"""
🌟 **A Wild Waifu Appeared!** 🌟

{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {rarity}

⚡ **First to smash claims her!**
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH!", callback_data=f"catch_{chat_id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image")
    
    try:
        if image_url:
            sent = await client.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=text,
                reply_markup=buttons
            )
        else:
            sent = await client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=buttons
            )
        
        active_spawns[chat_id]["message_id"] = sent.id
        
        # Auto expire after 60 seconds
        asyncio.create_task(expire_spawn(client, chat_id, sent.id))
        
    except Exception as e:
        print(f"❌ [AUTO-SPAWN] Error: {e}")


async def expire_spawn(client: Client, chat_id: int, message_id: int):
    """Expire unclaimed spawn after timeout"""
    await asyncio.sleep(60)  # 60 seconds timeout
    
    if chat_id in active_spawns:
        spawn_data = active_spawns[chat_id]
        if spawn_data.get("message_id") == message_id and not spawn_data.get("claimed"):
            # Waifu escaped!
            waifu = spawn_data.get("waifu", {})
            
            text = f"""
💨 **Waifu Escaped!**

**{waifu.get('name', 'Unknown')}** ran away!

Nobody claimed her in time... 😢
"""
            
            try:
                await client.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=text,
                    reply_markup=None
                )
            except:
                try:
                    await client.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=None
                    )
                except:
                    pass
            
            # Remove from active spawns
            del active_spawns[chat_id]


# ═══════════════════════════════════════════════════════════════════
#  CATCH CALLBACK (For Auto Spawned Waifus)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^catch_(-?\d+)_(\d+)$"))
async def catch_callback(client: Client, callback: CallbackQuery):
    """Handle catch button for auto-spawned waifus"""
    
    data = callback.data.split("_")
    chat_id = int(data[1])
    waifu_id = int(data[2])
    user = callback.from_user
    
    print(f"💥 [CATCH] {user.first_name} trying to catch waifu {waifu_id} in {chat_id}")
    
    # Check if spawn exists and not claimed
    if chat_id not in active_spawns:
        await callback.answer("❌ This waifu is no longer available!", show_alert=True)
        return
    
    spawn_data = active_spawns[chat_id]
    
    if spawn_data.get("claimed"):
        claimed_by = spawn_data.get("claimed_by", "Someone")
        await callback.answer(f"❌ Already claimed by {claimed_by}!", show_alert=True)
        return
    
    waifu = spawn_data.get("waifu")
    
    if not waifu or waifu.get("id") != waifu_id:
        await callback.answer("❌ Invalid waifu!", show_alert=True)
        return
    
    # FIRST COME FIRST SERVE - Mark as claimed immediately
    active_spawns[chat_id]["claimed"] = True
    active_spawns[chat_id]["claimed_by"] = user.first_name
    
    wm = get_waifu_manager()
    
    # Get or create user
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except:
        pass
    
    # Add to collection
    try:
        db.add_waifu_to_collection(user.id, waifu)
    except Exception as e:
        print(f"⚠️ [CATCH] Collection error: {e}")
    
    # Add coins based on rarity
    rarity = waifu.get("rarity", "common")
    coins = {"common": 10, "rare": 25, "epic": 50, "legendary": 100}.get(rarity, 10)
    
    try:
        db.add_coins(user.id, coins)
    except:
        pass
    
    # Update stats
    try:
        db.increment_user_stats(user.id, "total_wins")
        db.increment_user_stats(user.id, "total_smash")
    except:
        pass
    
    rarity_emoji = wm.get_rarity_emoji(rarity)
    
    text = f"""
🎉 **Waifu Claimed!**

{rarity_emoji} **{waifu.get('name')}** was caught by **{user.mention}**!

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
💰 Coins: +{coins}

Congratulations! 🎊
"""
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=None)
        else:
            await callback.message.edit_text(text=text, reply_markup=None)
    except Exception as e:
        print(f"⚠️ [CATCH] Edit error: {e}")
    
    await callback.answer(f"🎉 You caught {waifu.get('name')}!", show_alert=True)
    
    # Remove from active spawns
    if chat_id in active_spawns:
        del active_spawns[chat_id]


# ═══════════════════════════════════════════════════════════════════
#  /smash Command (Original - Unchanged)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["smash", "waifu", "sp"], config.COMMAND_PREFIX))
async def smash_command(client: Client, message: Message):
    """Start a new smash or pass game"""
    user = message.from_user
    
    print(f"🎮 [SMASH] /smash from {user.first_name} ({user.id})")
    
    try:
        wm = get_waifu_manager()
    except Exception as e:
        print(f"❌ [SMASH] WaifuManager error: {e}")
        await message.reply_text(f"❌ Error loading waifus: {e}")
        return
    
    # Get or create user
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except Exception as e:
        print(f"⚠️ [SMASH] DB error: {e}")
    
    # Check cooldown
    try:
        on_cooldown, remaining = db.check_cooldown(user.id, "smash")
        if on_cooldown:
            await message.reply_text(
                f"⏳ **Cooldown!**\n\n"
                f"Please wait **{Utils.format_time(remaining)}** before playing again!"
            )
            return
    except Exception as e:
        print(f"⚠️ [SMASH] Cooldown error: {e}")
    
    # Get random waifu
    waifu = wm.get_random_waifu()
    
    print(f"🎲 [SMASH] Got waifu: {waifu.get('name') if waifu else 'None'}")
    
    if not waifu:
        await message.reply_text(
            "❌ **No waifus available!**\n\n"
            "Please check `data/waifus.json` file."
        )
        return
    
    # Store active game
    active_games[user.id] = waifu
    
    # Format waifu card
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    rarity = waifu.get("rarity", "common").title()
    
    text = f"""
{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {rarity}

**What will you do?**
💥 Smash = Add to collection!
👋 Pass = Skip to next waifu
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    # Send with image if available
    image_url = waifu.get("image")
    
    try:
        if image_url:
            await message.reply_photo(
                photo=image_url,
                caption=text,
                reply_markup=buttons
            )
        else:
            await message.reply_text(text, reply_markup=buttons)
    except Exception as e:
        print(f"⚠️ [SMASH] Image failed: {e}")
        await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  Smash Button Callback (Original - Unchanged)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^smash_(\d+)_(\d+)$"))
async def smash_callback(client: Client, callback: CallbackQuery):
    """Handle smash button click"""
    
    print(f"💥 [SMASH] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    # Check if correct user
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ This is not your game!", show_alert=True)
        return
    
    user = callback.from_user
    wm = get_waifu_manager()
    
    # Get waifu from active games
    if user.id not in active_games:
        await callback.answer("❌ Game expired! Use /smash again.", show_alert=True)
        return
    
    waifu = active_games.pop(user.id)
    
    if waifu.get("id") != waifu_id:
        await callback.answer("❌ Invalid game! Use /smash again.", show_alert=True)
        return
    
    # Set cooldown
    try:
        db.set_cooldown(user.id, "smash", getattr(config, 'GAME_COOLDOWN', 30))
    except Exception as e:
        print(f"⚠️ [SMASH] Cooldown error: {e}")
    
    # Update stats
    try:
        db.increment_user_stats(user.id, "total_smash")
    except:
        pass
    
    # Direct win - no chance calculation for /smash command
    try:
        db.increment_user_stats(user.id, "total_wins")
    except:
        pass
    
    rarity = waifu.get("rarity", "common")
    
    # Add coins based on rarity
    coins = {"common": 10, "rare": 25, "epic": 50, "legendary": 100}.get(rarity, 10)
    
    try:
        db.add_coins(user.id, coins)
    except:
        pass
    
    # Add waifu to collection
    try:
        db.add_waifu_to_collection(user.id, waifu)
    except Exception as e:
        print(f"⚠️ [SMASH] Collection error: {e}")
    
    rarity_emoji = wm.get_rarity_emoji(rarity)
    
    text = f"""
🎉 **SMASH SUCCESS!**

{rarity_emoji} **{waifu.get('name')}** joined your collection!

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
💰 Coins earned: +{coins}

Use /collection to see your waifus!
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Play Again", callback_data="play_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="view_collection")
        ]
    ])
    
    # Update message
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text=text, reply_markup=buttons)
    except Exception as e:
        print(f"⚠️ [SMASH] Edit error: {e}")
        try:
            await callback.message.reply_text(text, reply_markup=buttons)
        except:
            pass
    
    await callback.answer("💥 Smashed!")


# ═══════════════════════════════════════════════════════════════════
#  Pass Button Callback (Original - Unchanged)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pass_(\d+)_(\d+)$"))
async def pass_callback(client: Client, callback: CallbackQuery):
    """Handle pass button click"""
    
    print(f"👋 [PASS] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    # Check if correct user
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ This is not your game!", show_alert=True)
        return
    
    user = callback.from_user
    wm = get_waifu_manager()
    
    # Remove from active games
    if user.id in active_games:
        active_games.pop(user.id)
    
    # Update stats
    try:
        db.increment_user_stats(user.id, "total_pass")
    except:
        pass
    
    # Get new waifu immediately
    waifu = wm.get_random_waifu()
    
    if not waifu:
        await callback.answer("❌ No more waifus!", show_alert=True)
        return
    
    # Store new game
    active_games[user.id] = waifu
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    rarity = waifu.get("rarity", "common").title()
    
    text = f"""
👋 **Passed!** Here's another one:

{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {rarity}

**What will you do?**
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image")
    
    try:
        if image_url:
            await callback.message.delete()
            await callback.message.reply_photo(
                photo=image_url,
                caption=text,
                reply_markup=buttons
            )
        else:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                await callback.message.edit_text(text=text, reply_markup=buttons)
    except Exception as e:
        print(f"⚠️ [PASS] Error: {e}")
        try:
            await callback.message.reply_text(text, reply_markup=buttons)
        except:
            pass
    
    await callback.answer("👋 Passed!")


# ═══════════════════════════════════════════════════════════════════
#  Play Again Callback (Original - Unchanged)
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^play_smash$"))
async def play_smash_callback(client: Client, callback: CallbackQuery):
    """Handle play smash button"""
    user = callback.from_user
    
    print(f"🎮 [PLAY] Callback from {user.first_name}")
    
    wm = get_waifu_manager()
    
    # Get or create user
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except:
        pass
    
    # Check cooldown
    try:
        on_cooldown, remaining = db.check_cooldown(user.id, "smash")
        if on_cooldown:
            await callback.answer(
                f"⏳ Cooldown! Wait {Utils.format_time(remaining)}",
                show_alert=True
            )
            return
    except:
        pass
    
    # Get random waifu
    waifu = wm.get_random_waifu()
    
    if not waifu:
        await callback.answer("❌ No waifus available!", show_alert=True)
        return
    
    # Store active game
    active_games[user.id] = waifu
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    rarity = waifu.get("rarity", "common").title()
    
    text = f"""
{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {rarity}

**What will you do?**
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image")
    
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
    except Exception as e:
        print(f"❌ [PLAY] Error: {e}")
        try:
            await callback.message.reply_text(text, reply_markup=buttons)
        except:
            pass
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
#  ADMIN COMMANDS FOR SPAWN CONTROL
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["spawninfo", "si"], config.COMMAND_PREFIX) & filters.group)
async def spawn_info_command(client: Client, message: Message):
    """Check spawn status in current chat"""
    chat_id = message.chat.id
    
    if chat_id not in chat_spawn_data:
        await message.reply_text("📊 No spawn data for this chat yet!")
        return
    
    data = chat_spawn_data[chat_id]
    unique_users = len(data.get("messages", set()))
    message_count = data.get("count", 0)
    last_spawn = data.get("last_spawn")
    
    # Calculate next spawn threshold
    if message_count < SPAWN_MESSAGE_MIN:
        next_threshold = SPAWN_MESSAGE_MIN
        next_rarity = "Common"
    elif message_count < SPAWN_MESSAGE_RARE:
        next_threshold = SPAWN_MESSAGE_RARE
        next_rarity = "Rare"
    elif message_count < SPAWN_MESSAGE_EPIC:
        next_threshold = SPAWN_MESSAGE_EPIC
        next_rarity = "Epic"
    else:
        next_threshold = SPAWN_MESSAGE_LEGENDARY
        next_rarity = "Legendary"
    
    text = f"""
📊 **Spawn Status**

💬 Messages: {message_count}
👥 Unique Users: {unique_users}
🎯 Next Threshold: {next_threshold} ({next_rarity})

⏰ Last Spawn: {last_spawn.strftime('%H:%M:%S') if last_spawn else 'Never'}
"""
    
    await message.reply_text(text)


@Client.on_message(filters.command(["forcespawn", "fs"], config.COMMAND_PREFIX) & filters.group)
async def force_spawn_command(client: Client, message: Message):
    """Force spawn a waifu (Admin only)"""
    user = message.from_user
    
    # Check if admin
    if user.id != getattr(config, 'OWNER_ID', 0) and user.id not in getattr(config, 'SUDO_USERS', []):
        return
    
    # Get rarity from command
    rarity = "common"
    if len(message.command) > 1:
        rarity = message.command[1].lower()
        if rarity not in ["common", "rare", "epic", "legendary"]:
            rarity = "common"
    
    await spawn_waifu(client, message.chat, rarity)
    await message.delete()
