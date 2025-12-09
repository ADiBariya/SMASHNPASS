# modules/smash.py - Main Game Module with Sexy Captions & Progress Bar

import random
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InputMediaPhoto,
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

**Commands:**
/smash - Start a new game
/waifu - Same as smash
/sp - Short command

**Admin Commands:**
/autodel <seconds> - Set auto-delete time (10-300)
/autodel off - Disable auto-delete
/autodelstatus - Check current setting
"""

# Store active games {user_id: waifu_data}
active_games = {}

# Track recently shown waifus per user
recent_waifus = {}

# Auto-delete settings per group
auto_delete_settings = {}

DEFAULT_AUTO_DELETE = 30


# ═══════════════════════════════════════════════════════════════════
#  🔥 SEXY CAPTION GENERATORS
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
    power = waifu.get('power', 0)
    
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

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📺 **Anime:** {anime}
┃ 💎 **Rarity:** {rarity}
┃ ⚔️ **Power:** {power}
┃ 💰 **Coins:** +{coins}
┗━━━━━━━━━━━━━━━━━━━━━━┛

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
    power = waifu.get('power', 0)
    
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

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📺 **Anime:** {anime}
┃ 💎 **Rarity:** {rarity}
┃ ⚔️ **Power:** {power}
┗━━━━━━━━━━━━━━━━━━━━━━┛

{random.choice(flirt_lines)}
"""


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
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def get_auto_delete_time(chat_id: int) -> int:
    """Get auto-delete time for a chat"""
    return auto_delete_settings.get(chat_id, DEFAULT_AUTO_DELETE)


async def is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


async def auto_delete_message(message: Message, delay: int):
    """Delete message after delay"""
    if delay <= 0:
        return
    
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception as e:
        print(f"⚠️ [AUTO-DEL] Could not delete: {e}")


def get_unique_waifu(wm, user_id: int):
    """Get a waifu that hasn't been shown recently"""
    
    if user_id not in recent_waifus:
        recent_waifus[user_id] = []
    
    recent_list = recent_waifus[user_id]
    max_attempts = 50
    
    for _ in range(max_attempts):
        waifu = wm.get_random_waifu()
        if not waifu:
            return None
        
        waifu_id = waifu.get("id")
        
        if waifu_id not in recent_list:
            recent_list.append(waifu_id)
            if len(recent_list) > 10:
                recent_list.pop(0)
            return waifu
    
    return wm.get_random_waifu()


# ═══════════════════════════════════════════════════════════════════
#  Auto-Delete Admin Commands
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["autodel", "autodelete"]) & filters.group)
async def set_auto_delete(client: Client, message: Message):
    """Set auto-delete time for smash results"""
    
    user = message.from_user
    chat_id = message.chat.id
    
    is_admin = await is_group_admin(client, chat_id, user.id)
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if not is_admin and user.id != owner_id:
        await message.reply_text("❌ Only admins can change this!")
        return
    
    args = message.text.split()[1:]
    
    if not args:
        await message.reply_text(
            "**🗑️ Auto-Delete Settings**\n\n"
            "`/autodel <seconds>` - Set time (10-300)\n"
            "`/autodel off` - Disable\n\n"
            "**Example:** `/autodel 30`"
        )
        return
    
    value = args[0].lower()
    
    if value in ["off", "disable", "0"]:
        auto_delete_settings[chat_id] = 0
        await message.reply_text("✅ Auto-Delete disabled!")
        return
    
    try:
        seconds = int(value)
    except ValueError:
        await message.reply_text("❌ Enter a valid number!")
        return
    
    if seconds < 10 or seconds > 300:
        await message.reply_text("❌ Must be between 10-300 seconds!")
        return
    
    auto_delete_settings[chat_id] = seconds
    await message.reply_text(f"✅ Auto-Delete set to **{seconds}s**!")


@Client.on_message(filters.command(["autodelstatus", "delstatus"]) & filters.group)
async def auto_delete_status(client: Client, message: Message):
    """Check auto-delete status"""
    
    chat_id = message.chat.id
    current = get_auto_delete_time(chat_id)
    
    if current > 0:
        status = f"✅ **{current} seconds**"
    else:
        status = "❌ Disabled"
    
    await message.reply_text(f"🗑️ Auto-Delete: {status}")


# ═══════════════════════════════════════════════════════════════════
#  /smash Command
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
    
    try:
        db.get_or_create_user(user.id, user.username, user.first_name)
    except Exception as e:
        print(f"⚠️ [SMASH] DB error: {e}")
    
    # Check cooldown
    try:
        on_cooldown, remaining = db.check_cooldown(user.id, "smash")
        if on_cooldown:
            await message.reply_text(
                f"⏳ **Chill bro!**\n\n"
                f"Wait **{Utils.format_time(remaining)}** before hunting again! 🔥"
            )
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
#  Smash Button Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^smash_(\d+)_(\d+)$"))
async def smash_callback(client: Client, callback: CallbackQuery):
    """Handle smash button with sexy animations"""
    
    print(f"💥 [SMASH] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ Get your own baddie!", show_alert=True)
        return
    
    user = callback.from_user
    chat_id = callback.message.chat.id
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
    
    is_win = Utils.calculate_win(win_chance)
    
    # Start progress animation
    asyncio.create_task(show_progress_bar(callback, waifu.get('name', 'Unknown'), is_win))
    
    # Show sexy loading caption
    loading_text = get_smash_loading_caption(waifu.get('name', 'Unknown'))
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=loading_text, reply_markup=None)
        else:
            await callback.message.edit_text(text=loading_text, reply_markup=None)
    except:
        pass
    
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
    
    delete_time = get_auto_delete_time(chat_id)
    delete_notice = f"\n\n🗑️ _Deleting in {delete_time}s_" if delete_time > 0 else ""
    
    if is_win:
        try:
            db.increment_user_stats(user.id, "total_wins")
        except:
            pass
        
        # Get coins
        try:
            if hasattr(wm, 'rarity_points'):
                coins = wm.rarity_points.get(rarity, 10)
            else:
                coins = {"common": 10, "rare": 100, "epic": 25, "legendary": 50}.get(rarity, 10)
        except:
            coins = {"common": 10, "rare": 100, "epic": 25, "legendary": 50}.get(rarity, 10)
        
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
                InlineKeyboardButton("🔥 Hunt Again", callback_data="play_smash"),
                InlineKeyboardButton("📦 My Baddies", callback_data="view_collection")
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
    
    # Update message
    result_message = None
    try:
        if callback.message.photo:
            result_message = await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            result_message = await callback.message.edit_text(text=text, reply_markup=buttons)
    except Exception as e:
        print(f"⚠️ [SMASH] Edit error: {e}")
        try:
            result_message = await callback.message.reply_text(text, reply_markup=buttons)
        except:
            pass
    
    if result_message and delete_time > 0:
        asyncio.create_task(auto_delete_message(callback.message, delete_time))


# ═══════════════════════════════════════════════════════════════════
#  Pass Button Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pass_(\d+)_(\d+)$"))
async def pass_callback(client: Client, callback: CallbackQuery):
    """Handle pass button"""
    
    print(f"👋 [PASS] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ Not your game!", show_alert=True)
        return
    
    user = callback.from_user
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
    
    try:
        if callback.message.photo:
            if image_url:
                try:
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=image_url, caption=text),
                        reply_markup=buttons
                    )
                except:
                    await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text=text, reply_markup=buttons)
            
    except Exception as e:
        print(f"⚠️ [PASS] Edit failed: {e}")
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
        except:
            pass
    
    pass_responses = [
        "👋 Next baddie loading...",
        "🔄 Alright, check this one!",
        "👀 Here's another one!",
        "✨ New challenger!",
    ]
    await callback.answer(random.choice(pass_responses))


# ═══════════════════════════════════════════════════════════════════
#  Play Again Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^play_smash$"))
async def play_smash_callback(client: Client, callback: CallbackQuery):
    """Handle play smash button"""
    user = callback.from_user
    
    print(f"🎮 [PLAY] Callback from {user.first_name}")
    
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
    
    try:
        if callback.message.photo:
            if image_url:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text=text, reply_markup=buttons)
    except:
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
    
    start_responses = [
        "🎮 Let's hunt some baddies!",
        "🔥 New game started!",
        "💥 Time to smash!",
        "😈 Let's get it!",
    ]
    await callback.answer(random.choice(start_responses))
