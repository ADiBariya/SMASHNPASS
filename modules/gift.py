from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from config import COMMAND_PREFIX
from helpers.utils import get_rarity_emoji
from datetime import datetime

__MODULE__ = "Gift"
__HELP__ = """
🎁 **Gift Commands**

`.gift @user <waifu_id>` - Gift a waifu
`.gift @user coins <amount>` - Gift coins
`.gifthistory` - View gift history
`.received` - View received gifts

**Notes:**
• Gifts are permanent and cannot be reversed
• Minimum 100 coins for coin gifts
"""


@Client.on_message(filters.command(["gift", "give"], prefixes=COMMAND_PREFIX))
async def gift_cmd(client: Client, message: Message):
    """Gift waifu or coins to another user"""
    user_id = message.from_user.id
    args = message.command[1:]
    
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`.gift @user <waifu_id>` - Gift waifu\n"
            "`.gift @user coins <amount>` - Gift coins"
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
    
    # Validations
    if target_id == user_id:
        return await message.reply_text("❌ You can't gift to yourself!")
    
    if target.is_bot:
        return await message.reply_text("❌ You can't gift to bots!")
    
    remaining_args = args[args_start:]
    
    if not remaining_args:
        return await message.reply_text("❌ Specify what to gift!")
    
    # Check if gifting coins
    if remaining_args[0].lower() == "coins":
        if len(remaining_args) < 2:
            return await message.reply_text("❌ Specify amount!")
        
        try:
            amount = int(remaining_args[1])
        except:
            return await message.reply_text("❌ Invalid amount!")
        
        if amount < 100:
            return await message.reply_text("❌ Minimum gift is 100 coins!")
        
        # Check user balance
        user_data = await db.get_user(user_id)
        if user_data.get("coins", 0) < amount:
            return await message.reply_text("❌ Not enough coins!")
        
        # Create confirmation
        buttons = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"giftcoins_{target_id}_{amount}"),
                InlineKeyboardButton("❌ Cancel", callback_data="gift_cancel")
            ]
        ]
        
        return await message.reply_text(
            f"🎁 **Confirm Coin Gift**\n\n"
            f"**To:** {target.mention}\n"
            f"**Amount:** {amount:,} coins\n\n"
            f"Are you sure?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    # Gifting waifu
    try:
        waifu_id = int(remaining_args[0])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")
    
    # Check if user owns waifu
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await message.reply_text("❌ You don't own this waifu!")
    
    # Create confirmation
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"giftwaifu_{target_id}_{waifu_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="gift_cancel")
        ]
    ]
    
    await message.reply_text(
        f"🎁 **Confirm Waifu Gift**\n\n"
        f"**To:** {target.mention}\n\n"
        f"**Waifu:**\n"
        f"{emoji} {waifu['name']}\n"
        f"📺 {waifu.get('anime', 'Unknown')}\n"
        f"⭐ {waifu.get('rarity', 'Common')}\n\n"
        f"⚠️ This action cannot be undone!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^giftcoins_(\d+)_(\d+)$"))
async def gift_coins_callback(client: Client, callback: CallbackQuery):
    """Confirm coin gift"""
    user_id = callback.from_user.id
    target_id = int(callback.matches[0].group(1))
    amount = int(callback.matches[0].group(2))
    
    # Check balance again
    user_data = await db.get_user(user_id)
    if user_data.get("coins", 0) < amount:
        return await callback.answer("❌ Not enough coins!", show_alert=True)
    
    # Transfer coins
    await db.update_coins(user_id, -amount)
    await db.update_coins(target_id, amount)
    
    # Log gift
    gift_log = {
        "type": "coins",
        "from_id": user_id,
        "to_id": target_id,
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$push": {"gifts_sent": gift_log}}
    )
    
    await db.users.update_one(
        {"user_id": target_id},
        {"$push": {"gifts_received": gift_log}},
        upsert=True
    )
    
    try:
        target = await client.get_users(target_id)
        target_name = target.first_name
    except:
        target_name = "User"
    
    await callback.message.edit_text(
        f"✅ **Gift Sent!**\n\n"
        f"**To:** {target_name}\n"
        f"**Amount:** {amount:,} coins\n\n"
        f"🎉 They have been notified!"
    )
    
    # Notify recipient
    try:
        sender = callback.from_user
        await client.send_message(
            target_id,
            f"🎁 **You received a gift!**\n\n"
            f"**From:** {sender.first_name}\n"
            f"**Amount:** {amount:,} coins\n\n"
            f"💰 Added to your balance!"
        )
    except:
        pass
    
    await callback.answer("Gift sent!")


@Client.on_callback_query(filters.regex(r"^giftwaifu_(\d+)_(\d+)$"))
async def gift_waifu_callback(client: Client, callback: CallbackQuery):
    """Confirm waifu gift"""
    user_id = callback.from_user.id
    target_id = int(callback.matches[0].group(1))
    waifu_id = int(callback.matches[0].group(2))
    
    # Check ownership again
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)
    
    # Transfer waifu
    await db.remove_from_collection(user_id, waifu_id)
    
    waifu_copy = waifu.copy()
    waifu_copy["gifted_from"] = user_id
    waifu_copy["gifted_at"] = datetime.now().strftime("%Y-%m-%d")
    
    await db.add_to_collection(target_id, waifu_copy)
    
    # Log gift
    gift_log = {
        "type": "waifu",
        "from_id": user_id,
        "to_id": target_id,
        "waifu_name": waifu["name"],
        "waifu_id": waifu_id,
        "timestamp": datetime.now().isoformat()
    }
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$push": {"gifts_sent": gift_log}}
    )
    
    await db.users.update_one(
        {"user_id": target_id},
        {"$push": {"gifts_received": gift_log}},
        upsert=True
    )
    
    try:
        target = await client.get_users(target_id)
        target_name = target.first_name
    except:
        target_name = "User"
    
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    
    await callback.message.edit_text(
        f"✅ **Waifu Gifted!**\n\n"
        f"**To:** {target_name}\n\n"
        f"**Waifu:**\n"
        f"{emoji} {waifu['name']}\n"
        f"⭐ {waifu.get('rarity', 'Common')}\n\n"
        f"🎉 They have been notified!"
    )
    
    # Notify recipient
    try:
        sender = callback.from_user
        await client.send_message(
            target_id,
            f"🎁 **You received a waifu gift!**\n\n"
            f"**From:** {sender.first_name}\n\n"
            f"**Waifu:**\n"
            f"{emoji} {waifu['name']}\n"
            f"📺 {waifu.get('anime', 'Unknown')}\n"
            f"⭐ {waifu.get('rarity', 'Common')}\n\n"
            f"💝 Added to your collection!"
        )
    except:
        pass
    
    await callback.answer("Waifu gifted!")


@Client.on_callback_query(filters.regex("^gift_cancel$"))
async def gift_cancel_callback(client: Client, callback: CallbackQuery):
    """Cancel gift"""
    await callback.message.edit_text("❌ Gift cancelled.")
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^giftsel_(\d+)$"))
async def gift_select_callback(client: Client, callback: CallbackQuery):
    """Select recipient for gift from profile"""
    waifu_id = int(callback.matches[0].group(1))
    
    await callback.message.reply_text(
        f"🎁 **Gift Waifu**\n\n"
        f"Reply to someone's message with:\n"
        f"`.gift @user {waifu_id}`\n\n"
        f"Or use: `.gift <username> {waifu_id}`"
    )
    await callback.answer()


@Client.on_message(filters.command(["gifthistory", "giftsent"], prefixes=COMMAND_PREFIX))
async def gift_history_cmd(client: Client, message: Message):
    """View sent gifts history"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    gifts = user_data.get("gifts_sent", [])
    
    if not gifts:
        return await message.reply_text("📭 You haven't sent any gifts yet!")
    
    text = "📤 **Gifts Sent**\n\n"
    
    for gift in gifts[-10:]:  # Last 10 gifts
        gift_type = gift.get("type", "unknown")
        
        try:
            recipient = await client.get_users(gift["to_id"])
            recipient_name = recipient.first_name
        except:
            recipient_name = f"User {gift['to_id']}"
        
        if gift_type == "coins":
            text += f"💰 {gift['amount']:,} coins → {recipient_name}\n"
        else:
            text += f"🎴 {gift.get('waifu_name', 'Unknown')} → {recipient_name}\n"
    
    text += f"\n📊 **Total Gifts:** {len(gifts)}"
    
    await message.reply_text(text)


@Client.on_message(filters.command(["received", "giftreceived"], prefixes=COMMAND_PREFIX))
async def received_gifts_cmd(client: Client, message: Message):
    """View received gifts"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    gifts = user_data.get("gifts_received", [])
    
    if not gifts:
        return await message.reply_text("📭 You haven't received any gifts yet!")
    
    text = "📥 **Gifts Received**\n\n"
    
    for gift in gifts[-10:]:  # Last 10 gifts
        gift_type = gift.get("type", "unknown")
        
        try:
            sender = await client.get_users(gift["from_id"])
            sender_name = sender.first_name
        except:
            sender_name = f"User {gift['from_id']}"
        
        if gift_type == "coins":
            text += f"💰 {gift['amount']:,} coins ← {sender_name}\n"
        else:
            text += f"🎴 {gift.get('waifu_name', 'Unknown')} ← {sender_name}\n"
    
    text += f"\n📊 **Total Received:** {len(gifts)}"
    
    await message.reply_text(text)


@Client.on_message(filters.command(["sell", "sellwaifu"], prefixes=COMMAND_PREFIX))
async def sell_waifu_cmd(client: Client, message: Message):
    """Sell a waifu for coins"""
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.sell <waifu_id>`")
    
    try:
        waifu_id = int(message.command[1])
    except:
        return await message.reply_text("❌ Invalid waifu ID!")
    
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await message.reply_text("❌ You don't own this waifu!")
    
    # Calculate sell price (50% of value)
    value = waifu.get("value", 100)
    sell_price = value // 2
    
    buttons = [
        [
            InlineKeyboardButton("✅ Sell", callback_data=f"confirmsell_{waifu_id}_{sell_price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="gift_cancel")
        ]
    ]
    
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    
    await message.reply_text(
        f"💰 **Sell Waifu**\n\n"
        f"{emoji} {waifu['name']}\n"
        f"⭐ {waifu.get('rarity', 'Common')}\n\n"
        f"**Value:** {value:,} coins\n"
        f"**Sell Price:** {sell_price:,} coins (50%)\n\n"
        f"⚠️ This action cannot be undone!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^confirmsell_(\d+)_(\d+)$"))
async def confirm_sell_callback(client: Client, callback: CallbackQuery):
    """Confirm waifu sale"""
    user_id = callback.from_user.id
    waifu_id = int(callback.matches[0].group(1))
    sell_price = int(callback.matches[0].group(2))
    
    # Check ownership
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)
    
    # Remove waifu and add coins
    await db.remove_from_collection(user_id, waifu_id)
    await db.update_coins(user_id, sell_price)
    
    await callback.message.edit_text(
        f"✅ **Waifu Sold!**\n\n"
        f"**Sold:** {waifu['name']}\n"
        f"**Received:** {sell_price:,} coins"
    )
    await callback.answer("Sold!")