from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database import db
from config import COMMAND_PREFIX
from helpers.utils import get_rarity_emoji
from datetime import datetime

__MODULE__ = "Gift"
__HELP__ = """
🎁 **Gift Commands**

`.gift @user <waifu_id>` - Gift waifu
`.gift @user coins <amount>` - Gift coins
`.gifthistory` - View gift history
`.received` - View received gifts

• Gifts are permanent
• Minimum 100 coins for coin gifts
"""

# =============================================================
#  Helper Functions
# =============================================================

def get_user_waifus(user_id: int):
    """Get user's waifus from collections table"""
    return list(db.collections.find({"user_id": user_id}))

def find_waifu_by_id(user_id: int, waifu_id: int):
    """Find a waifu by ID in user's collection"""
    return db.collections.find_one({
        "user_id": user_id,
        "waifu_id": waifu_id
    })

# =============================================================
#  GIFT COMMAND
# =============================================================
@Client.on_message(filters.command(["gift", "give"], prefixes=COMMAND_PREFIX))
async def gift_cmd(client: Client, message: Message):
    """Gift waifu or coins to another user"""
    user_id = message.from_user.id
    args = message.command[1:]

    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`.gift @user <waifu_id>`\n"
            "`.gift @user coins <amount>`"
        )

    # Get target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        args_start = 0
    else:
        try:
            target = await client.get_users(args[0])
            args_start = 1
        except:
            return await message.reply_text("❌ User not found!")

    target_id = target.id

    if target_id == user_id:
        return await message.reply_text("❌ You can't gift yourself!")

    if target.is_bot:
        return await message.reply_text("❌ You can't gift a bot!")

    remaining_args = args[args_start:]
    if not remaining_args:
        return await message.reply_text("❌ Specify what to gift!")

    # =============================================================
    #  COIN GIFT
    # =============================================================
    if remaining_args[0].lower() == "coins":
        if len(remaining_args) < 2:
            return await message.reply_text("❌ Specify amount!")

        try:
            amount = int(remaining_args[1])
        except:
            return await message.reply_text("❌ Invalid amount!")

        if amount < 100:
            return await message.reply_text("❌ Minimum gift is 100 coins!")

        user_data = db.get_user(user_id)
        if user_data.get("coins", 0) < amount:
            return await message.reply_text("❌ Not enough coins!")

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"giftcoins_{target_id}_{amount}"),
                InlineKeyboardButton("❌ Cancel", callback_data="gift_cancel")
            ]
        ])

        target_name = target.first_name or "User"
        return await message.reply_text(
             f"🎁 **Confirm Coin Gift**\n\n"
             f"**To:** {target_name} (ID: {target.id})\n"
             f"**Amount:** {amount:,} coins\n\n"
             "Confirm?",
             reply_markup=buttons
        )

    # =============================================================
    #  WAIFU GIFT
    # =============================================================
    try:
        waifu_id = int(remaining_args[0])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")

    # Check if user owns this waifu in collections table
    waifu = find_waifu_by_id(user_id, waifu_id)

    if not waifu:
        return await message.reply_text("❌ You don't own this waifu!")

    emoji = get_rarity_emoji(waifu.get("waifu_rarity", "Common"))

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"giftwaifu_{target_id}_{waifu_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="gift_cancel")
        ]
    ])

    target_name = target.first_name or "User"
    await message.reply_text(
        f"🎁 **Confirm Waifu Gift**\n\n"
        f"**To:** {target_name} (ID: {target.id})\n\n"
        f"{emoji} **{waifu.get('waifu_name', 'Unknown')}**\n"
        f"📺 {waifu.get('waifu_anime', 'Unknown')}\n"
        f"⭐ {waifu.get('waifu_rarity', 'Common')}\n\n"
        f"⚠️ This action cannot be undone!",
        reply_markup=buttons
    )

# =============================================================
#  COIN GIFT CALLBACK (CONFIRM)
# =============================================================
@Client.on_callback_query(filters.regex(r"^giftcoins_(\d+)_(\d+)$"))
async def gift_coins_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.matches[0].group(1))
    amount = int(callback.matches[0].group(2))

    # Recheck balance
    user_data = db.get_user(user_id)
    if user_data.get("coins", 0) < amount:
        return await callback.answer("❌ Not enough coins!", show_alert=True)

    # Ensure target exists in DB
    db.users.update_one(
        {"user_id": target_id},
        {"$setOnInsert": {"coins": 0, "collection": []}},
        upsert=True
    )

    # Transfer
    db.remove_coins(user_id, amount)
    db.add_coins(target_id, amount)

    # Log
    gift_log = {
        "type": "coins",
        "from_id": user_id,
        "to_id": target_id,
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }

    db.users.update_one({"user_id": user_id}, {"$push": {"gifts_sent": gift_log}})
    db.users.update_one({"user_id": target_id}, {"$push": {"gifts_received": gift_log}}, upsert=True)

    await callback.message.edit_text(
        f"✅ **Coins Sent!**\n\n"
        f"To: `{target_id}`\n"
        f"Amount: {amount:,}"
    )

    # Notify target
    try:
        sender = callback.from_user
        sender_name = sender.first_name or "Someone"
        await client.send_message(
            target_id,
            f"🎁 **You received a gift!**\n\n"
            f"From: {sender_name}\n"
            f"Amount: {amount:,} coins"
        )
    except:
        pass

    await callback.answer("Gift sent!")

# =============================================================
#  WAIFU GIFT CALLBACK - FIXED
# =============================================================
@Client.on_callback_query(filters.regex(r"^giftwaifu_(\d+)_(\d+)$"))
async def gift_waifu_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.matches[0].group(1))
    waifu_id = int(callback.matches[0].group(2))

    # Check if user still owns this waifu
    waifu = find_waifu_by_id(user_id, waifu_id)
    if not waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)

    # Get waifu details for transfer
    waifu_name = waifu.get("waifu_name", "Unknown")
    waifu_anime = waifu.get("waifu_anime", "Unknown")
    waifu_rarity = waifu.get("waifu_rarity", "Common")
    waifu_power = waifu.get("waifu_power", 0)
    waifu_image = waifu.get("waifu_image", "")

    # Remove from sender's collection
    db.collections.delete_one({
        "user_id": user_id,
        "waifu_id": waifu_id
    })

    # Add to receiver's collection
    new_waifu_entry = {
        "user_id": target_id,
        "waifu_id": waifu_id,
        "waifu_name": waifu_name,
        "waifu_anime": waifu_anime,
        "waifu_rarity": waifu_rarity,
        "waifu_power": waifu_power,
        "waifu_image": waifu_image,
        "obtained_at": datetime.now(),
        "obtained_method": "gift",
        "gifted_from": user_id
    }
    db.collections.insert_one(new_waifu_entry)

    # Log
    gift_log = {
        "type": "waifu",
        "from_id": user_id,
        "to_id": target_id,
        "waifu_name": waifu_name,
        "waifu_id": waifu_id,
        "timestamp": datetime.now().isoformat()
    }

    db.users.update_one({"user_id": user_id}, {"$push": {"gifts_sent": gift_log}})
    db.users.update_one({"user_id": target_id}, {"$push": {"gifts_received": gift_log}}, upsert=True)

    emoji = get_rarity_emoji(waifu_rarity)

    await callback.message.edit_text(
        f"🎁 **Waifu Gifted!**\n\n"
        f"{emoji} {waifu_name}"
    )

    # Notify
    try:
        sender = callback.from_user
        sender_name = sender.first_name or "Someone"
        await client.send_message(
            target_id,
            f"🎁 **New Waifu Gift!**\n\n"
            f"From: {sender_name}\n"
            f"{emoji} {waifu_name}"
        )
    except:
        pass

    await callback.answer("Gifted!")

# =============================================================
#  CANCEL
# =============================================================
@Client.on_callback_query(filters.regex("^gift_cancel$"))
async def gift_cancel_callback(client: Client, callback: CallbackQuery):
    await callback.message.edit_text("❌ Gift cancelled.")
    await callback.answer()

# =============================================================
#  GIFT HISTORY
# =============================================================
@Client.on_message(filters.command(["gifthistory", "giftsent"], prefixes=COMMAND_PREFIX))
async def gift_history_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = db.get_user(user_id)

    gifts = user_data.get("gifts_sent", [])
    if not gifts:
        return await message.reply_text("📭 No gifts sent yet!")

    text = "📤 **Gifts Sent**\n\n"

    for gift in gifts[-10:]:
        if gift["type"] == "coins":
            text += f"💰 {gift['amount']:,} → User {gift['to_id']}\n"
        else:
            text += f"🎴 {gift.get('waifu_name')} → User {gift['to_id']}\n"

    text += f"\n📊 Total: {len(gifts)}"

    await message.reply_text(text)

# =============================================================
#  RECEIVED GIFTS
# =============================================================
@Client.on_message(filters.command(["received", "giftreceived"], prefixes=COMMAND_PREFIX))
async def received_gifts_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = db.get_user(user_id)

    gifts = user_data.get("gifts_received", [])
    if not gifts:
        return await message.reply_text("📭 No gifts received!")

    text = "📥 **Gifts Received**\n\n"

    for gift in gifts[-10:]:
        if gift["type"] == "coins":
            text += f"💰 {gift['amount']:,} ← User {gift['from_id']}\n"
        else:
            text += f"🎴 {gift.get('waifu_name')} ← User {gift['from_id']}\n"

    text += f"\n📊 Total: {len(gifts)}"

    await message.reply_text(text)
