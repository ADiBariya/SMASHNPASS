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
STREAK_BONUS_PERCENT = 10
MAX_STREAK_BONUS = 100
COOLDOWN_HOURS = 24


@Client.on_message(filters.command(["daily", "claim"], prefixes=COMMAND_PREFIX))
async def daily_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = db.get_user(user_id)  # FIXED

    last_daily = user_data.get("last_daily") if user_data else None

    if last_daily:
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

        if time_diff < timedelta(hours=48):
            new_streak = user_data.get("daily_streak", 0) + 1
        else:
            new_streak = 1
    else:
        new_streak = 1

    base_reward = random.randint(BASE_REWARD_MIN, BASE_REWARD_MAX)

    streak_bonus_percent = min(new_streak * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)
    streak_bonus = int(base_reward * (streak_bonus_percent / 100))

    total_reward = base_reward + streak_bonus

    db.users.update_one(   # FIXED
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

    text = f"""
🎁 **Daily Reward Claimed!**

💰 **Base Reward:** {base_reward:,} coins
🔥 **Streak Bonus:** +{streak_bonus:,} coins ({streak_bonus_percent}%)
━━━━━━━━━━━━━━━━
💵 **Total:** {total_reward:,} coins

🔥 **Current Streak:** {new_streak} days
"""

    if new_streak % 7 == 0:
        text += f"\n🎉 **7-Day Streak Bonus!** Use `.bonus` to claim a free waifu!"

    buttons = [[InlineKeyboardButton("📊 View Streak", callback_data="streak_view")]]

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command(["streak", "mystreak"], prefixes=COMMAND_PREFIX))
async def streak_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = db.get_user(user_id)  # FIXED

    streak = user_data.get("daily_streak", 0) if user_data else 0
    last_daily = user_data.get("last_daily") if user_data else None

    bonus_percent = min(streak * STREAK_BONUS_PERCENT, MAX_STREAK_BONUS)

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

    streak_bar = ""
    for i in range(1, 8):
        if i <= (streak % 7) or (streak % 7 == 0 and streak > 0):
            streak_bar += "🟢"
        else:
            streak_bar += "⚫"

    days_to_bonus = 7 - (streak % 7) if streak % 7 != 0 else 0

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
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)  # FIXED

    streak = user_data.get("daily_streak", 0) if user_data else 0
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
    from helpers.utils import load_waifus

    user_id = message.from_user.id
    user_data = db.get_user(user_id)  # FIXED

    streak = user_data.get("daily_streak", 0)
    last_bonus = user_data.get("last_streak_bonus")

    if streak < 7:
        return await message.reply_text(
            f"❌ You need a 7-day streak!\n\n"
            f"**Current Streak:** {streak} days\n"
            f"**Days Needed:** {7 - streak}"
        )

    bonus_tier = streak // 7
    last_tier_claimed = user_data.get("last_bonus_tier", 0)

    if last_tier_claimed >= bonus_tier:
        return await message.reply_text(
            f"❌ Bonus already claimed!\n\n"
            f"Continue your streak to unlock the next bonus."
        )

    waifus = load_waifus()

    # rarity weights (same as your code)
    if bonus_tier >= 4:
        weights = {"Rare": 30, "Legendary": 25, "Epic": 25, "Common": 0}
    elif bonus_tier >= 3:
        weights = {"Rare": 25, "Legendary": 20, "Epic": 30, "Common": 5}
    elif bonus_tier >= 2:
        weights = {"Rare": 20, "Legendary": 15, "Epic": 35, "Common": 10}
    else:
        weights = {"Rare": 10, "Legendary": 10, "Epic": 30, "Common": 50}

    rarities = [r for r, w in weights.items() if w > 0]
    rarity_weights = [weights[r] for r in rarities]

    selected_rarity = random.choices(rarities, weights=rarity_weights)[0]
    rarity_waifus = [w for w in waifus if w.get("rarity") == selected_rarity]

    if not rarity_waifus:
        rarity_waifus = waifus

    waifu = random.choice(rarity_waifus)

    waifu_copy = waifu.copy()
    waifu_copy["obtained_at"] = datetime.now().strftime("%Y-%m-%d")
    waifu_copy["obtained_from"] = "streak_bonus"

    db.collections.insert_one({  # FIXED
        "user_id": user_id,
        **waifu_copy
    })

    db.users.update_one(  # FIXED
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
    user_id = message.from_user.id
    user_data = db.get_user(user_id)  # FIXED

    streak = user_data.get("daily_streak", 0)
    total_dailies = user_data.get("total_dailies", streak)

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
