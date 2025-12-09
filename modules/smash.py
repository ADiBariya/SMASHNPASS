# modules/smash.py - Main Game Module with Anti-Spam & Progress Bar

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

# Track recently shown waifus per user (to avoid repeats)
# {user_id: [last 10 waifu ids]}
recent_waifus = {}

# Auto-delete settings per group {chat_id: seconds}
auto_delete_settings = {}

# Default auto-delete time (0 = disabled)
DEFAULT_AUTO_DELETE = 30


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
    """Get a waifu that hasn't been shown recently to this user"""
    
    # Initialize recent tracking for user if needed
    if user_id not in recent_waifus:
        recent_waifus[user_id] = []
    
    recent_list = recent_waifus[user_id]
    max_attempts = 50  # Try up to 50 times to get unique waifu
    
    for _ in range(max_attempts):
        waifu = wm.get_random_waifu()
        if not waifu:
            return None
        
        waifu_id = waifu.get("id")
        
        # If waifu not in recent list, use it
        if waifu_id not in recent_list:
            # Add to recent list
            recent_list.append(waifu_id)
            
            # Keep only last 10 waifus in memory
            if len(recent_list) > 10:
                recent_list.pop(0)
            
            return waifu
    
    # If couldn't find unique after many attempts, just return any
    return wm.get_random_waifu()


async def show_progress_bar(callback: CallbackQuery, waifu_name: str, is_win: bool):
    """Show progress bar animation while smashing"""
    
    progress_stages = [
        "💥 Smashing...\n▱▱▱▱▱",
        "💥 Smashing...\n▰▱▱▱▱",
        "💥 Smashing...\n▰▰▱▱▱",
        "💥 Smashing...\n▰▰▰▱▱",
        "💥 Smashing...\n▰▰▰▰▱",
        "💥 Smashing...\n▰▰▰▰▰"
    ]
    
    # Show progress animation
    for stage in progress_stages:
        try:
            await callback.answer(stage, show_alert=False)
            await asyncio.sleep(0.3)
        except:
            pass
    
    # Final result
    if is_win:
        await callback.answer(f"🎉 Success! You caught {waifu_name}!", show_alert=True)
    else:
        await callback.answer(f"💔 Failed! {waifu_name} rejected you!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  Auto-Delete Admin Commands
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["autodel", "autodelete"]) & filters.group)
async def set_auto_delete(client: Client, message: Message):
    """Set auto-delete time for smash results"""
    
    user = message.from_user
    chat_id = message.chat.id
    
    # Check admin
    is_admin = await is_group_admin(client, chat_id, user.id)
    owner_id = getattr(config, 'OWNER_ID', 0)
    
    if not is_admin and user.id != owner_id:
        await message.reply_text("❌ Only admins can change auto-delete settings!")
        return
    
    args = message.text.split()[1:]
    
    if not args:
        await message.reply_text(
            "**Usage:**\n"
            "`/autodel <seconds>` - Set time (10-300)\n"
            "`/autodel off` - Disable auto-delete\n\n"
            "**Example:**\n"
            "`/autodel 30` - Delete after 30 seconds"
        )
        return
    
    value = args[0].lower()
    
    if value in ["off", "disable", "0"]:
        auto_delete_settings[chat_id] = 0
        await message.reply_text(
            "✅ **Auto-Delete Disabled!**\n\n"
            "Smash results will not be deleted automatically."
        )
        return
    
    try:
        seconds = int(value)
    except ValueError:
        await message.reply_text("❌ Please enter a valid number!")
        return
    
    if seconds < 10 or seconds > 300:
        await message.reply_text("❌ Value must be between 10 and 300 seconds!")
        return
    
    auto_delete_settings[chat_id] = seconds
    
    await message.reply_text(
        f"✅ **Auto-Delete Set!**\n\n"
        f"Smash results will be deleted after **{seconds} seconds**."
    )


@Client.on_message(filters.command(["autodelstatus", "delstatus"]) & filters.group)
async def auto_delete_status(client: Client, message: Message):
    """Check auto-delete status"""
    
    chat_id = message.chat.id
    current = get_auto_delete_time(chat_id)
    
    if current > 0:
        status = f"✅ Enabled - **{current} seconds**"
    else:
        status = "❌ Disabled"
    
    await message.reply_text(f"🗑️ **Auto-Delete Status:** {status}")


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
    
    # Get unique waifu (avoid recent repeats)
    waifu = get_unique_waifu(wm, user.id)
    
    print(f"🎲 [SMASH] Got waifu: {waifu.get('name') if waifu else 'None'}")
    
    if not waifu:
        await message.reply_text(
            "❌ **No waifus available!**\n\n"
            "Admin needs to add waifus in the database channel."
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
⚔️ **Power:** {waifu.get('power', 0)}

**What will you do?**
💥 Smash = Try to win her!
👋 Pass = Skip to next waifu
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    # Send with image if available
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
#  Smash Button Callback with Progress Bar
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^smash_(\d+)_(\d+)$"))
async def smash_callback(client: Client, callback: CallbackQuery):
    """Handle smash button click with progress animation"""
    
    print(f"💥 [SMASH] Callback: {callback.data}")
    
    data = callback.data.split("_")
    game_user_id = int(data[1])
    waifu_id = int(data[2])
    
    # Check if correct user
    if callback.from_user.id != game_user_id:
        await callback.answer("❌ This is not your game!", show_alert=True)
        return
    
    user = callback.from_user
    chat_id = callback.message.chat.id
    wm = get_waifu_manager()
    
    # Get waifu from active games
    if user.id not in active_games:
        await callback.answer("❌ Game expired! Use /smash again.", show_alert=True)
        return
    
    waifu = active_games.pop(user.id)
    
    if waifu.get("id") != waifu_id:
        await callback.answer("❌ Invalid game! Use /smash again.", show_alert=True)
        return
    
    # Calculate win/lose FIRST (before showing progress)
    win_chance = getattr(config, 'WIN_CHANCE', 60)
    
    # Rarity affects win chance
    rarity = waifu.get("rarity", "common")
    if rarity == "legendary":
        win_chance -= 20
    elif rarity == "epic":
        win_chance -= 10
    elif rarity == "rare":
        win_chance -= 5
    
    is_win = Utils.calculate_win(win_chance)
    
    # Show progress bar animation
    asyncio.create_task(show_progress_bar(callback, waifu.get('name', 'Unknown'), is_win))
    
    # Show "Smashing..." status while processing
    processing_text = f"""
💥 **SMASHING...**

Processing your attempt for **{waifu.get('name')}**...
"""
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=processing_text, reply_markup=None)
        else:
            await callback.message.edit_text(text=processing_text, reply_markup=None)
    except:
        pass
    
    # Wait a bit for dramatic effect
    await asyncio.sleep(2)
    
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
    
    print(f"🎲 [SMASH] Chance: {win_chance}%, Result: {'WIN' if is_win else 'LOSE'}")
    
    rarity_emoji = wm.get_rarity_emoji(rarity)
    
    # Get auto-delete time
    delete_time = get_auto_delete_time(chat_id)
    delete_notice = f"\n\n🗑️ _This message will be deleted in {delete_time}s_" if delete_time > 0 else ""
    
    if is_win:
        # User wins!
        try:
            db.increment_user_stats(user.id, "total_wins")
        except:
            pass
        
        # FIX: Get coins based on rarity using proper method or fallback
        try:
            # Try using rarity_points dictionary if it exists
            if hasattr(wm, 'rarity_points'):
                coins = wm.rarity_points.get(rarity, 10)
            else:
                # Fallback to hardcoded values matching your requirements
                coins = {"common": 10, "rare": 100, "epic": 25, "legendary": 50}.get(rarity, 10)
        except:
            # Ultimate fallback
            coins = {"common": 10, "rare": 100, "epic": 25, "legendary": 50}.get(rarity, 10)
        
        try:
            db.add_coins(user.id, coins)
        except:
            pass
        
        # Add waifu to collection
        try:
            db.add_waifu_to_collection(user.id, waifu)
        except Exception as e:
            print(f"⚠️ [SMASH] Collection error: {e}")
        
        text = f"""
🎉 **SMASH SUCCESS!**

{rarity_emoji} **{waifu.get('name')}** joined your collection!

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
⚔️ Power: {waifu.get('power')}
💰 Coins earned: +{coins}

Use /collection to see your waifus!{delete_notice}
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Play Again", callback_data="play_smash"),
                InlineKeyboardButton("📦 Collection", callback_data="view_collection")
            ]
        ])
        
    else:
        # User loses
        try:
            db.increment_user_stats(user.id, "total_losses")
        except:
            pass
        
        text = f"""
💔 **SMASH FAILED!**

{rarity_emoji} **{waifu.get('name')}** rejected you!

Better luck next time! 😢

**Tip:** Legendary waifus are harder to win!{delete_notice}
"""
        
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
    
    # Schedule auto-delete
    if result_message and delete_time > 0:
        asyncio.create_task(auto_delete_message(callback.message, delete_time))


# ═══════════════════════════════════════════════════════════════════
#  Pass Button Callback - Edit Message to Avoid Spam
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^pass_(\d+)_(\d+)$"))
async def pass_callback(client: Client, callback: CallbackQuery):
    """Handle pass button click - Edit message instead of new"""
    
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
    
    # Get new unique waifu
    waifu = get_unique_waifu(wm, user.id)
    
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
⚔️ **Power:** {waifu.get('power', 0)}

**What will you do?**
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    # Try to edit existing message first (to avoid spam)
    try:
        if callback.message.photo:
            # If current message has photo and new waifu also has photo
            if image_url:
                try:
                    # Try to edit with new photo
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=image_url, caption=text),
                        reply_markup=buttons
                    )
                except:
                    # If edit fails, just edit caption
                    await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                # New waifu has no image, just edit caption
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            # Text message - just edit
            await callback.message.edit_text(text=text, reply_markup=buttons)
            
    except Exception as e:
        print(f"⚠️ [PASS] Edit failed: {e}")
        # Only if edit fails completely, send new message
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
    
    await callback.answer("👋 Passed! New waifu loaded!")


# ═══════════════════════════════════════════════════════════════════
#  Play Again Callback
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
    
    # Get unique waifu
    waifu = get_unique_waifu(wm, user.id)
    
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
⚔️ **Power:** {waifu.get('power', 0)}

**What will you do?**
"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
            InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
        ]
    ])
    
    image_url = waifu.get("image") or waifu.get("file_id")
    
    # Try to edit first
    try:
        if callback.message.photo:
            if image_url:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
            else:
                await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text=text, reply_markup=buttons)
    except:
        # If edit fails, delete and send new
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
    
    await callback.answer("🎮 New game started!")