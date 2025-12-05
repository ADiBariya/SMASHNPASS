# modules/smash.py - Main Game Module

import random
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

print("🔄 [SMASH] Module imported!")

# Module info
__MODULE__ = "Smash"
__HELP__ = """
🎮 **Smash Game**
/smash - Start a new game
/waifu - Same as smash
/sp - Short command
"""

# Help data for this module
HELP = {
    "name": "Smash Game",
    "emoji": "🎮",
    "description": "The main Smash or Pass game",
    "commands": {
        "smash": "Start a new Smash or Pass game",
        "pass": "Skip current waifu (alias)"
    },
    "usage": "Use /smash to get a random waifu, then choose to Smash or Pass!"
}

# Store active games {user_id: waifu_data}
active_games = {}


def setup(app: Client):
    """Setup function called by loader"""
    
    print("⚙️ [SMASH] setup() called!")
    
    # Test waifu manager
    try:
        wm = get_waifu_manager()
        print(f"📊 [SMASH] WaifuManager: {len(wm.waifus)} waifus loaded")
    except Exception as e:
        print(f"❌ [SMASH] WaifuManager error: {e}")
    
    
    @app.on_message(filters.command(["smash", "waifu", "sp"], config.CMD_PREFIX))
    async def smash_command(client: Client, message: Message):
        """Start a new smash or pass game"""
        user = message.from_user
        
        print(f"🎮 [SMASH] /smash from {user.first_name} ({user.id})")
        
        try:
            wm = get_waifu_manager()
        except Exception as e:
            print(f"❌ [SMASH] WaifuManager error: {e}")
            await message.reply_text(f"❌ Error: {e}")
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
            print(f"⚠️ [SMASH] Cooldown error (ignoring): {e}")
        
        # Get random waifu
        waifu = wm.get_random_waifu()
        
        print(f"🎲 [SMASH] Got waifu: {waifu.get('name') if waifu else 'None'}")
        
        if not waifu:
            await message.reply_text(
                "❌ **No waifus available!**\n\n"
                "Check `data/waifus.json` file."
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
        image_url = waifu.get("image")
        
        try:
            if image_url:
                await message.reply_photo(
                    photo=image_url,
                    caption=text,
                    reply_markup=buttons
                )
                print(f"✅ [SMASH] Sent with image")
            else:
                await message.reply_text(text, reply_markup=buttons)
                print(f"✅ [SMASH] Sent without image")
        except Exception as e:
            print(f"⚠️ [SMASH] Image failed: {e}")
            try:
                await message.reply_text(text, reply_markup=buttons)
            except Exception as e2:
                print(f"❌ [SMASH] Text also failed: {e2}")
    
    
    @app.on_callback_query(filters.regex(r"^smash_(\d+)_(\d+)$"))
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
            db.set_cooldown(user.id, "smash", config.GAME_COOLDOWN)
        except Exception as e:
            print(f"⚠️ [SMASH] Cooldown set error: {e}")
        
        # Update stats
        try:
            db.increment_user_stats(user.id, "total_smash")
        except Exception as e:
            print(f"⚠️ [SMASH] Stats error: {e}")
        
        # Calculate win/lose
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
        
        print(f"🎲 [SMASH] Chance: {win_chance}%, Result: {'WIN' if is_win else 'LOSE'}")
        
        rarity_emoji = wm.get_rarity_emoji(rarity)
        
        if is_win:
            # User wins!
            try:
                db.increment_user_stats(user.id, "total_wins")
            except:
                pass
            
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
            
            text = f"""
🎉 **SMASH SUCCESS!**

{rarity_emoji} **{waifu.get('name')}** joined your collection!

📺 Anime: {waifu.get('anime')}
💎 Rarity: {rarity.title()}
⚔️ Power: {waifu.get('power')}
💰 Coins earned: +{coins}

Use /collection to see your waifus!
"""
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎮 Play Again", callback_data="play_smash"),
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

**Tip:** Legendary waifus are harder to win!
"""
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎮 Try Again", callback_data="play_smash")
                ]
            ])
        
        # Update message
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons
                )
            else:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=buttons
                )
        except Exception as e:
            print(f"⚠️ [SMASH] Edit error: {e}")
            try:
                await callback.message.reply_text(text, reply_markup=buttons)
            except:
                pass
        
        await callback.answer("💥 Smashed!" if is_win else "💔 Rejected!")
    
    
    @app.on_callback_query(filters.regex(r"^pass_(\d+)_(\d+)$"))
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
        
        # Get new waifu immediately (no cooldown for pass)
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
⚔️ **Power:** {waifu.get('power', 0)}

**What will you do?**
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💥 SMASH", callback_data=f"smash_{user.id}_{waifu['id']}"),
                InlineKeyboardButton("👋 PASS", callback_data=f"pass_{user.id}_{waifu['id']}")
            ]
        ])
        
        # Update message
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
                    await callback.message.edit_caption(
                        caption=text,
                        reply_markup=buttons
                    )
                else:
                    await callback.message.edit_text(
                        text=text,
                        reply_markup=buttons
                    )
        except Exception as e:
            print(f"⚠️ [PASS] Error: {e}")
            try:
                await callback.message.reply_text(text, reply_markup=buttons)
            except:
                pass
        
        await callback.answer("👋 Passed!")
    
    
    @app.on_callback_query(filters.regex("^play_smash$"))
    async def play_smash_callback(client: Client, callback: CallbackQuery):
        """Handle play smash button from other menus"""
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
⚔️ **Power:** {waifu.get('power', 0)}

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
    
    
    print("✅ [SMASH] All handlers registered!")
