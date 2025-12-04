from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import COMMAND_PREFIX
from datetime import datetime, timedelta
import random

__MODULE__ = "Daily"
__HELP__ = """
📅 **Daily Commands**

`.daily` - Claim daily reward
`.streak` - View your daily streak
`.bonus` - Claim streak bonus (every 7 days)

**Rewards:**
• Base: 100-500 coins
• Streak Bonus: +10% per day (max 100%)
• 7-Day Bonus: Free random waifu!
"""

# Daily reward settings
BASE_REWARD_MIN = 100
BASE_REWARD_MAX = 500
STREAK_BONUS_PERCENT = 10  # 10% per streak day
MAX_STREAK_BONUS = 100  # Max 100% bonus
COOLDOWN_HOURS = 24


@Client.on_message(filters.command(["daily", "claim"], prefixes=COMMAND_PREFIX))
async def daily_cmd(client: Client, message: Message):
    """Claim daily reward"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    # Check cooldown
    last_daily = user_data.get("last_daily")
    
    if last_daily:
        # Parse datetime
        if isinstance(last_daily, str):
            last_daily = datetime.fromisoformat(last_daily)
        
        time_diff = datetime.now() - last_daily
        
        if time_diff < timedelta(hours=COOLDOWN_HOURS):
            remaining = timedelta(hours=COOLDOWN_HOURS) - time_diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            return await message.reply_text(
                f"⏰ **Daily Already Claimed!**\n\n"
                f"Come back in **{hours}h {minutes}m**"
            )
        
        # Check if streak continues or resets
        if time_diff < timedelta(hours=48):
            # Continue streak
            new_streak = user_data.get("daily_streak", 0) + 1
        else:
            # Reset streak
            new_streak = 1
    else:
        new_streak = 1
    
    # Calculate reward
    base_reward = random.randint(BASE_REWARD_MIN, BASE_REWARD_MAX)
    
    # Apply streak bonus
    streak_bonus_percent = min(new_streak * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)
    streak_bonus = int(base_reward * (streak_bonus_percent / 100))
    
    total_reward = base_reward + streak_bonus
    
    # Update user data
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "last_daily": datetime.now().isoformat(),
                "daily_streak": new_streak
            },
            "$inc": {
                "coins": total_reward,
                "total_earned": total_reward
            }
        },
        upsert=True
    )
    
    # Build response
    text = f"""
🎁 **Daily Reward Claimed!**

💰 **Base Reward:** {base_reward:,} coins
🔥 **Streak Bonus:** +{streak_bonus:,} coins ({streak_bonus_percent}%)
━━━━━━━━━━━━━━━━
💵 **Total:** {total_reward:,} coins

🔥 **Current Streak:** {new_streak} days
"""
    
    # Check for 7-day bonus
    if new_streak % 7 == 0:
        text += f"\n🎉 **7-Day Streak Bonus!** Use `.bonus` to claim a free waifu!"
    
    buttons = [[InlineKeyboardButton("📊 View Streak", callback_data="streak_view")]]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command(["streak", "mystreak"], prefixes=COMMAND_PREFIX))
async def streak_cmd(client: Client, message: Message):
    """View daily streak"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    streak = user_data.get("daily_streak", 0)
    last_daily = user_data.get("last_daily")
    
    # Calculate bonus percentage
    bonus_percent = min(streak * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)
    
    # Check streak status
    if last_daily:
        if isinstance(last_daily, str):
            last_daily = datetime.fromisoformat(last_daily)
        
        time_diff = datetime.now() - last_daily
        
        if time_diff > timedelta(hours=48):
            streak_status = "❌ Streak Lost!"
            streak = 0
        elif time_diff > timedelta(hours=COOLDOWN_HOURS):
            streak_status = "⚠️ Claim now or lose streak!"
        else:
            remaining = timedelta(hours=COOLDOWN_HOURS) - time_diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            streak_status = f"✅ Next in {hours}h {minutes}m"
    else:
        streak_status = "🆕 Start your streak!"
    
    # Build streak visualization
    streak_bar = ""
    for i in range(1, 8):
        if i <= (streak % 7) or (streak % 7 == 0 and streak > 0):
            streak_bar += "🟢"
        else:
            streak_bar += "⚫"
    
    days_to_bonus = 7 - (streak % 7) if streak % 7 != 0 else 0
    if streak > 0 and streak % 7 == 0:
        days_to_bonus = 0
    
    text = f"""
🔥 **Daily Streak**

**Current Streak:** {streak} days
**Status:** {streak_status}

📊 **Weekly Progress:**
{streak_bar}

💰 **Bonus Multiplier:** +{bonus_percent}%
🎁 **Days to Bonus:** {days_to_bonus if days_to_bonus > 0 else "Ready!"}

**Streak Rewards:**
• +10% coins per streak day
• Free waifu every 7 days!
"""
    
    await message.reply_text(text)


@Client.on_callback_query(filters.regex("^streak_view$"))
async def streak_view_callback(client, callback):
    """View streak from callback"""
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    
    streak = user_data.get("daily_streak", 0)
    bonus_percent = min(streak * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)
    
    streak_bar = ""
    for i in range(1, 8):
        if i <= (streak % 7) or (streak % 7 == 0 and streak > 0):
            streak_bar += "🟢"
        else:
            streak_bar += "⚫"
    
    await callback.answer(
        f"🔥 Streak: {streak} days | +{bonus_percent}% bonus\n{streak_bar}",
        show_alert=True
    )


@Client.on_message(filters.command(["bonus", "claimbonus"], prefixes=COMMAND_PREFIX))
async def bonus_cmd(client: Client, message: Message):
    """Claim 7-day streak bonus"""
    from helpers.utils import load_waifus, get_random_waifu
    
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    streak = user_data.get("daily_streak", 0)
    last_bonus = user_data.get("last_streak_bonus")
    
    # Check if eligible
    if streak < 7:
        return await message.reply_text(
            f"❌ You need a 7-day streak!\n\n"
            f"**Current Streak:** {streak} days\n"
            f"**Days Needed:** {7 - streak}"
        )
    
    # Check which bonus tier
    bonus_tier = streak // 7
    
    # Check if already claimed this tier
    last_tier_claimed = user_data.get("last_bonus_tier", 0)
    
    if last_tier_claimed >= bonus_tier:
        return await message.reply_text(
            f"❌ Bonus already claimed!\n\n"
            f"Continue your streak to unlock the next bonus."
        )
    
    # Get random waifu
    waifus = load_waifus()
    
    # Higher streak = better rarity chance
    if bonus_tier >= 4:
        weights = {"Legendary": 30, "Epic": 40, "Rare": 20, "Uncommon": 10, "Common": 0}
    elif bonus_tier >= 3:
        weights = {"Legendary": 20, "Epic": 35, "Rare": 30, "Uncommon": 15, "Common": 0}
    elif bonus_tier >= 2:
        weights = {"Legendary": 10, "Epic": 25, "Rare": 35, "Uncommon": 25, "Common": 5}
    else:
        weights = {"Legendary": 5, "Epic": 15, "Rare": 30, "Uncommon": 30, "Common": 20}
    
    # Filter by rarity
    rarities = []
    rarity_weights = []
    for rarity, weight in weights.items():
        if weight > 0:
            rarities.append(rarity)
            rarity_weights.append(weight)
    
    selected_rarity = random.choices(rarities, weights=rarity_weights)[0]
    
    rarity_waifus = [w for w in waifus if w.get("rarity") == selected_rarity]
    
    if not rarity_waifus:
        rarity_waifus = waifus
    
    waifu = random.choice(rarity_waifus)
    waifu_copy = waifu.copy()
    waifu_copy["obtained_at"] = datetime.now().strftime("%Y-%m-%d")
    waifu_copy["obtained_from"] = "streak_bonus"
    
    # Add to collection
    await db.add_to_collection(user_id, waifu_copy)
    
    # Update bonus tier
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"last_bonus_tier": bonus_tier}}
    )
    
    text = f"""
🎉 **Streak Bonus Claimed!**

🔥 **Streak:** {streak} days (Tier {bonus_tier})

**You received:**
━━━━━━━━━━━━━━━━
🎴 **{waifu['name']}**
📺 {waifu.get('anime', 'Unknown')}
⭐ {waifu.get('rarity', 'Common')}
━━━━━━━━━━━━━━━━

Keep your streak for better rewards!
"""
    
    if waifu.get("image"):
        await message.reply_photo(photo=waifu["image"], caption=text)
    else:
        await message.reply_text(text)


@Client.on_message(filters.command(["weekly", "weeklystats"], prefixes=COMMAND_PREFIX))
async def weekly_stats_cmd(client: Client, message: Message):
    """View weekly statistics"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    streak = user_data.get("daily_streak", 0)
    total_dailies = user_data.get("total_dailies", streak)
    
    # Calculate total bonus earned from streak
    total_streak_bonus = 0
    for day in range(1, streak + 1):
        bonus_percent = min(day * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)
        avg_base = (BASE_REWARD_MIN + BASE_REWARD_MAX) // 2
        total_streak_bonus += int(avg_base * (bonus_percent / 100))
    
    text = f"""
📅 **Weekly Statistics**

🔥 **Current Streak:** {streak} days
📊 **Total Claims:** {total_dailies}
💰 **Est. Streak Bonus:** ~{total_streak_bonus:,} coins

**Next Milestones:**
"""
    
    milestones = [7, 14, 21, 30, 60, 100]
    for milestone in milestones:
        if streak < milestone:
            days_left = milestone - streak
            text += f"\n• {milestone} days: {days_left} days left"
            break
    
    await message.reply_text(text)