# modules/admin.py - Admin Commands (UPDATED)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from config import COMMAND_PREFIX, OWNER_ID, SUDO_USERS
from helpers.utils import load_waifus, save_waifus
import json
import os

__MODULE__ = "Admin"
__HELP__ = """
👑 **Admin Commands** (Owner Only)

**💰 Coins:**
`.addcoins @user <amount>` - Add coins
`.removecoins @user <amount>` - Remove coins
`.setcoins @user <amount>` - Set exact coins

**🎴 Waifus:**
`.addwaifu` - Add new waifu (reply to JSON)
`.delwaifu <id>` - Delete waifu from database
`.givewaifu @user <id>` - Give waifu to user

**🗑️ Clear/Delete:**
`.clearuser @user` - Clear ALL user data
`.clearwaifus @user` - Clear only waifus
`.clearcoins @user` - Clear only coins

**👤 User Management:**
`.userinfo @user` - View user details
`.resetuser @user` - Reset user data
`.ban @user` - Ban user from bot
`.unban @user` - Unban user

**🔧 Bot:**
`.broadcast <msg>` - Broadcast to all users
`.botstats` - Bot statistics
`.sudo add/remove/list` - Manage sudo users
"""


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


# ═══════════════════════════════════════════════════════════════════
#  COINS COMMANDS
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["addcoins", "ac"], prefixes=COMMAND_PREFIX))
async def add_coins_cmd(client: Client, message: Message):
    """Add coins to user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text("❌ **Usage:** `.addcoins @user <amount>`")

    if amount <= 0:
        return await message.reply_text("❌ Amount must be positive!")

    success = db.add_coins(target.id, amount)

    if not success:
        return await message.reply_text("❌ Failed to add coins!")

    await message.reply_text(
        f"✅ **Coins Added!**\n\n"
        f"**User:** {target.mention}\n"
        f"**Amount:** +{amount:,} coins"
    )


@Client.on_message(filters.command(["removecoins", "rc"], prefixes=COMMAND_PREFIX))
async def remove_coins_cmd(client: Client, message: Message):
    """Remove coins from user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text("❌ **Usage:** `.removecoins @user <amount>`")

    if amount <= 0:
        return await message.reply_text("❌ Amount must be positive!")

    success = db.remove_coins(target.id, amount)

    if not success:
        return await message.reply_text("❌ Failed! Insufficient balance or user not found.")

    await message.reply_text(
        f"✅ **Coins Removed!**\n\n"
        f"**User:** {target.mention}\n"
        f"**Amount:** -{amount:,} coins"
    )


@Client.on_message(filters.command(["setcoins", "sc"], prefixes=COMMAND_PREFIX))
async def set_coins_cmd(client: Client, message: Message):
    """Set user coins to specific amount"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text("❌ **Usage:** `.setcoins @user <amount>`")

    if amount < 0:
        return await message.reply_text("❌ Amount cannot be negative!")

    # Get old coins
    user_data = db.get_user(target.id)
    old_coins = user_data.get("coins", 0) if user_data else 0

    # Set new coins
    db.users.update_one(
        {"user_id": target.id},
        {"$set": {"coins": amount}},
        upsert=True
    )

    await message.reply_text(
        f"✅ **Coins Set!**\n\n"
        f"**User:** {target.mention}\n"
        f"**Old:** {old_coins:,}\n"
        f"**New:** {amount:,}"
    )


# ═══════════════════════════════════════════════════════════════════
#  CLEAR/DELETE COMMANDS
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["clearuser", "deleteuser"], prefixes=COMMAND_PREFIX))
async def clear_user_cmd(client: Client, message: Message):
    """Clear ALL user data (waifus + coins + stats)"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ **Usage:** `.clearuser @user`")

    # Get current stats for display
    user_data = db.get_user(target.id)
    waifu_count = db.get_collection_count(target.id)
    coins = user_data.get("coins", 0) if user_data else 0

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Clear All", callback_data=f"adm_clearall_{target.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="adm_cancel")
        ]
    ])

    await message.reply_text(
        f"⚠️ **Clear ALL data for {target.mention}?**\n\n"
        f"👤 User ID: `{target.id}`\n"
        f"📦 Waifus: {waifu_count}\n"
        f"💰 Coins: {coins:,}\n\n"
        f"**This will delete:**\n"
        f"• All waifus\n"
        f"• All coins\n"
        f"• All stats\n"
        f"• Favorite waifu\n"
        f"• Cooldowns\n\n"
        f"⚠️ **This cannot be undone!**",
        reply_markup=buttons
    )


@Client.on_message(filters.command(["clearwaifus", "deletewaifus", "cw"], prefixes=COMMAND_PREFIX))
async def clear_waifus_cmd(client: Client, message: Message):
    """Clear only user's waifus"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ **Usage:** `.clearwaifus @user`")

    waifu_count = db.get_collection_count(target.id)

    if waifu_count == 0:
        return await message.reply_text(f"❌ {target.mention} has no waifus!")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Clear Waifus", callback_data=f"adm_clearwaifus_{target.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="adm_cancel")
        ]
    ])

    await message.reply_text(
        f"⚠️ **Clear all waifus for {target.mention}?**\n\n"
        f"📦 Total Waifus: {waifu_count}\n\n"
        f"⚠️ **This cannot be undone!**",
        reply_markup=buttons
    )


@Client.on_message(filters.command(["clearcoins", "deletecoins", "cc"], prefixes=COMMAND_PREFIX))
async def clear_coins_cmd(client: Client, message: Message):
    """Clear only user's coins (set to 0)"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ **Usage:** `.clearcoins @user`")

    user_data = db.get_user(target.id)
    coins = user_data.get("coins", 0) if user_data else 0

    if coins == 0:
        return await message.reply_text(f"❌ {target.mention} already has 0 coins!")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Clear Coins", callback_data=f"adm_clearcoins_{target.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="adm_cancel")
        ]
    ])

    await message.reply_text(
        f"⚠️ **Clear coins for {target.mention}?**\n\n"
        f"💰 Current Coins: {coins:,}\n\n"
        f"⚠️ **This cannot be undone!**",
        reply_markup=buttons
    )


# ═══════════════════════════════════════════════════════════════════
#  ADMIN CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^adm_clearall_(\d+)$"))
async def clear_all_callback(client: Client, callback: CallbackQuery):
    """Clear all user data callback"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Owner only!", show_alert=True)

    target_id = int(callback.data.split("_")[2])

    try:
        # Delete all waifus from collections
        deleted_waifus = db.collections.delete_many({"user_id": target_id})

        # Delete user document
        db.users.delete_one({"user_id": target_id})

        # Delete cooldowns
        db.cooldowns.delete_many({"user_id": target_id})

        await callback.message.edit_text(
            f"✅ **User Data Cleared!**\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"📦 Waifus deleted: {deleted_waifus.deleted_count}\n"
            f"👤 Profile: Deleted\n"
            f"⏰ Cooldowns: Cleared"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {e}")

    await callback.answer("✅ Cleared!")


@Client.on_callback_query(filters.regex(r"^adm_clearwaifus_(\d+)$"))
async def clear_waifus_callback(client: Client, callback: CallbackQuery):
    """Clear waifus callback"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Owner only!", show_alert=True)

    target_id = int(callback.data.split("_")[2])

    try:
        # Delete all waifus
        result = db.collections.delete_many({"user_id": target_id})

        # Also clear favorite
        db.users.update_one(
            {"user_id": target_id},
            {"$unset": {"favorite_waifu": ""}}
        )

        await callback.message.edit_text(
            f"✅ **Waifus Cleared!**\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"📦 Deleted: {result.deleted_count} waifus"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {e}")

    await callback.answer("✅ Waifus cleared!")


@Client.on_callback_query(filters.regex(r"^adm_clearcoins_(\d+)$"))
async def clear_coins_callback(client: Client, callback: CallbackQuery):
    """Clear coins callback"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Owner only!", show_alert=True)

    target_id = int(callback.data.split("_")[2])

    try:
        # Get old coins
        user_data = db.get_user(target_id)
        old_coins = user_data.get("coins", 0) if user_data else 0

        # Set coins to 0
        db.users.update_one(
            {"user_id": target_id},
            {"$set": {"coins": 0}}
        )

        await callback.message.edit_text(
            f"✅ **Coins Cleared!**\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"💰 Old: {old_coins:,}\n"
            f"💰 New: 0"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {e}")

    await callback.answer("✅ Coins cleared!")


@Client.on_callback_query(filters.regex(r"^adm_cancel$"))
async def admin_cancel_callback(client: Client, callback: CallbackQuery):
    """Cancel admin action"""
    await callback.message.edit_text("❌ **Cancelled!**")
    await callback.answer("Cancelled!")


# ═══════════════════════════════════════════════════════════════════
#  USER INFO COMMAND
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["userinfo", "uinfo", "ui"], prefixes=COMMAND_PREFIX))
async def user_info_cmd(client: Client, message: Message):
    """View detailed user info"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ **Usage:** `.userinfo @user`")

    # Get user data
    user_data = db.get_user(target.id)
    waifu_count = db.get_collection_count(target.id)

    if not user_data:
        return await message.reply_text(f"❌ User `{target.id}` not found in database!")

    # Get rarity breakdown
    legendary = db.collections.count_documents({"user_id": target.id, "waifu_rarity": "legendary"})
    epic = db.collections.count_documents({"user_id": target.id, "waifu_rarity": "epic"})
    rare = db.collections.count_documents({"user_id": target.id, "waifu_rarity": "rare"})
    common = db.collections.count_documents({"user_id": target.id, "waifu_rarity": "common"})

    text = f"""
👤 **User Info**

🆔 **ID:** `{target.id}`
📛 **Username:** @{target.username or 'N/A'}
📝 **Name:** {target.first_name or 'N/A'}

💰 **Economy**
├ Coins: {user_data.get('coins', 0):,}
├ Earned: {user_data.get('total_earned', 0):,}
└ Spent: {user_data.get('total_spent', 0):,}

📦 **Collection** ({waifu_count} total)
├ 🟡 Legendary: {legendary}
├ 🟣 Epic: {epic}
├ 🔵 Rare: {rare}
└ ⚪ Common: {common}

📊 **Stats**
├ Smash: {user_data.get('total_smash', 0)}
├ Pass: {user_data.get('total_pass', 0)}
├ Wins: {user_data.get('total_wins', 0)}
└ Losses: {user_data.get('total_losses', 0)}

⭐ **Favorite:** {user_data.get('favorite_waifu', 'None')}
🔥 **Streak:** {user_data.get('daily_streak', 0)}
🚫 **Banned:** {'Yes' if user_data.get('banned') else 'No'}
"""

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Clear All", callback_data=f"adm_clearall_{target.id}"),
            InlineKeyboardButton("📦 Clear Waifus", callback_data=f"adm_clearwaifus_{target.id}")
        ],
        [
            InlineKeyboardButton("💰 Clear Coins", callback_data=f"adm_clearcoins_{target.id}")
        ]
    ])

    await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  GIVE WAIFU COMMAND
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["givewaifu", "gw"], prefixes=COMMAND_PREFIX))
async def give_waifu_cmd(client: Client, message: Message):
    """Give a waifu to user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    # Parse arguments
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            waifu_id = int(message.command[1]) if len(message.command) > 1 else None
        except:
            return await message.reply_text("❌ Invalid waifu ID!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            waifu_id = int(message.command[2])
        except:
            return await message.reply_text("❌ Invalid user or waifu ID!")
    else:
        return await message.reply_text("❌ **Usage:** `.givewaifu @user <waifu_id>`")

    if not waifu_id:
        return await message.reply_text("❌ Specify waifu ID!")

    # Find waifu
    waifus = load_waifus()
    waifu = None
    for w in waifus:
        if w.get("id") == waifu_id:
            waifu = w
            break

    if not waifu:
        return await message.reply_text(f"❌ Waifu ID `{waifu_id}` not found!")

    # Add waifu to collection
    waifu_data = {
        "id": waifu.get("id"),
        "name": waifu.get("name"),
        "anime": waifu.get("anime"),
        "rarity": waifu.get("rarity", "common").lower(),
        "image": waifu.get("image", ""),
        "obtained_method": "admin_gift"
    }

    db.add_to_collection(target.id, waifu_data)

    emoji = {
        "legendary": "🟡",
        "epic": "🟣",
        "rare": "🔵",
        "common": "⚪"
    }.get(waifu.get("rarity", "common").lower(), "⚪")

    await message.reply_text(
        f"✅ **Waifu Given!**\n\n"
        f"**To:** {target.mention}\n"
        f"{emoji} **{waifu.get('name')}**\n"
        f"📺 {waifu.get('anime')}\n"
        f"🆔 `{waifu_id}`"
    )


# ═══════════════════════════════════════════════════════════════════
#  EXISTING COMMANDS (UNCHANGED)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["addwaifu", "aw"], prefixes=COMMAND_PREFIX))
async def add_waifu_cmd(client: Client, message: Message):
    """Add new waifu to database"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply_text(
            "❌ Reply to a message with waifu JSON!\n\n"
            "**Format:**\n"
            "```json\n"
            "{\n"
            '  "name": "Waifu Name",\n'
            '  "anime": "Anime Name",\n'
            '  "rarity": "legendary",\n'
            '  "image": "image_url"\n'
            "}\n"
            "```"
        )

    try:
        waifu_data = json.loads(message.reply_to_message.text)
    except json.JSONDecodeError:
        return await message.reply_text("❌ Invalid JSON format!")

    required = ["name", "anime", "rarity"]
    for field in required:
        if field not in waifu_data:
            return await message.reply_text(f"❌ Missing field: `{field}`")

    waifus = load_waifus()
    max_id = max([w.get("id", 0) for w in waifus], default=0)
    waifu_data["id"] = max_id + 1

    waifus.append(waifu_data)
    save_waifus(waifus)

    await message.reply_text(
        f"✅ **Waifu Added!**\n\n"
        f"**Name:** {waifu_data['name']}\n"
        f"**Anime:** {waifu_data['anime']}\n"
        f"**Rarity:** {waifu_data['rarity']}\n"
        f"**ID:** {waifu_data['id']}"
    )


@Client.on_message(filters.command(["delwaifu", "dw"], prefixes=COMMAND_PREFIX))
async def del_waifu_cmd(client: Client, message: Message):
    """Delete waifu from database"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.delwaifu <waifu_id>`")

    try:
        waifu_id = int(message.command[1])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")

    waifus = load_waifus()

    removed = None
    for i, w in enumerate(waifus):
        if w.get("id") == waifu_id:
            removed = waifus.pop(i)
            break

    if not removed:
        return await message.reply_text("❌ Waifu not found!")

    save_waifus(waifus)

    await message.reply_text(
        f"✅ **Waifu Deleted!**\n\n"
        f"**Name:** {removed['name']}\n"
        f"**ID:** {removed['id']}"
    )


@Client.on_message(filters.command(["broadcast", "bc"], prefixes=COMMAND_PREFIX))
async def broadcast_cmd(client: Client, message: Message):
    """Broadcast message to all users"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text("❌ **Usage:** `.broadcast <message>` or reply to a message")

    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
        broadcast_text = None
    else:
        broadcast_msg = None
        broadcast_text = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""

    all_users = list(db.users.find({}))

    success = 0
    failed = 0

    status_msg = await message.reply_text("📤 Broadcasting...")

    for user in all_users:
        try:
            user_id = user.get("user_id")
            if not user_id:
                failed += 1
                continue
            if broadcast_msg:
                await broadcast_msg.copy(user_id)
            else:
                await client.send_message(user_id, broadcast_text)
            success += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"📤 **Sent:** {success}\n"
        f"❌ **Failed:** {failed}"
    )


@Client.on_message(filters.command(["botstats", "bstats"], prefixes=COMMAND_PREFIX))
async def bot_stats_cmd(client: Client, message: Message):
    """View bot statistics"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    try:
        total_users = db.users.count_documents({})
    except Exception:
        total_users = 0

    try:
        total_groups = db.groups.count_documents({}) if hasattr(db, "groups") else 0
    except Exception:
        total_groups = 0

    waifus = load_waifus()

    try:
        total_collected = db.collections.count_documents({})
    except Exception:
        total_collected = 0

    # Rarity breakdown
    try:
        legendary = db.collections.count_documents({"waifu_rarity": "legendary"})
        epic = db.collections.count_documents({"waifu_rarity": "epic"})
        rare = db.collections.count_documents({"waifu_rarity": "rare"})
        common = db.collections.count_documents({"waifu_rarity": "common"})
    except:
        legendary = epic = rare = common = 0

    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$coins", 0]}}}}
    ]
    try:
        result = list(db.users.aggregate(pipeline))
        total_coins = result[0]["total"] if result else 0
    except Exception:
        total_coins = 0

    text = f"""
📊 **Bot Statistics**

👥 **Users:** {total_users:,}
👥 **Groups:** {total_groups:,}

📦 **Waifus Available:** {len(waifus):,}
🎴 **Total Collected:** {total_collected:,}
├ 🟡 Legendary: {legendary:,}
├ 🟣 Epic: {epic:,}
├ 🔵 Rare: {rare:,}
└ ⚪ Common: {common:,}

💰 **Coins in Circulation:** {total_coins:,}
"""

    await message.reply_text(text)


@Client.on_message(filters.command(["sudo"], prefixes=COMMAND_PREFIX))
async def sudo_cmd(client: Client, message: Message):
    """Manage sudo users"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`.sudo add @user` - Add sudo\n"
            "`.sudo remove @user` - Remove sudo\n"
            "`.sudo list` - List sudos"
        )

    action = message.command[1].lower()

    if action == "list":
        if not SUDO_USERS:
            return await message.reply_text("📭 No sudo users!")

        text = "👑 **Sudo Users:**\n\n"
        for user_id in SUDO_USERS:
            try:
                user = await client.get_users(user_id)
                text += f"• {user.mention} (`{user_id}`)\n"
            except:
                text += f"• Unknown (`{user_id}`)\n"

        return await message.reply_text(text)

    if len(message.command) < 3 and not message.reply_to_message:
        return await message.reply_text("❌ Specify a user!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        try:
            target = await client.get_users(message.command[2])
        except:
            return await message.reply_text("❌ User not found!")

    if action == "add":
        if target.id in SUDO_USERS:
            return await message.reply_text("❌ Already a sudo user!")

        SUDO_USERS.append(target.id)
        return await message.reply_text(f"✅ Added {target.mention} as sudo!")

    elif action == "remove":
        if target.id not in SUDO_USERS:
            return await message.reply_text("❌ Not a sudo user!")

        SUDO_USERS.remove(target.id)
        return await message.reply_text(f"✅ Removed {target.mention} from sudo!")


@Client.on_message(filters.command(["ban", "banuser"], prefixes=COMMAND_PREFIX))
async def ban_user_cmd(client: Client, message: Message):
    """Ban user from bot"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ Specify a user!")

    if target.id == OWNER_ID:
        return await message.reply_text("❌ Can't ban owner!")

    db.users.update_one(
        {"user_id": target.id},
        {"$set": {"banned": True}},
        upsert=True
    )

    await message.reply_text(f"🔨 Banned {target.mention} from bot!")


@Client.on_message(filters.command(["unban", "unbanuser"], prefixes=COMMAND_PREFIX))
async def unban_user_cmd(client: Client, message: Message):
    """Unban user from bot"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ Specify a user!")

    db.users.update_one(
        {"user_id": target.id},
        {"$set": {"banned": False}}
    )

    await message.reply_text(f"✅ Unbanned {target.mention}!")


@Client.on_message(filters.command(["resetuser", "reset"], prefixes=COMMAND_PREFIX))
async def reset_user_cmd(client: Client, message: Message):
    """Reset user data (same as clearuser but without confirmation)"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only command!")

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ Specify a user!")

    # Delete waifus
    deleted = db.collections.delete_many({"user_id": target.id})

    # Delete user
    db.users.delete_one({"user_id": target.id})

    # Delete cooldowns
    db.cooldowns.delete_many({"user_id": target.id})

    await message.reply_text(
        f"🗑️ **Reset Complete!**\n\n"
        f"**User:** {target.mention}\n"
        f"📦 Waifus deleted: {deleted.deleted_count}"
    )
