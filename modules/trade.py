from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from config import COMMAND_PREFIX
import asyncio

# Active trades storage
active_trades = {}

__MODULE__ = "Trade"
__HELP__ = """
🔄 **Trade Commands**

`.trade @user <waifu_id>` - Send trade request
`.accept` - Accept incoming trade
`.decline` - Decline incoming trade
`.cancel` - Cancel your trade request
`.mytrades` - View pending trades

**How Trading Works:**
1. Use `.trade @user waifu_id` to initiate
2. Other user selects their waifu to trade
3. Both confirm to complete trade
"""


@Client.on_message(filters.command(["trade", "tr"], prefixes=COMMAND_PREFIX))
async def trade_cmd(client: Client, message: Message):
    """Initiate a trade with another user"""
    user_id = message.from_user.id
    
    # Check if user already has active trade
    if user_id in active_trades:
        return await message.reply_text("❌ You already have an active trade! Cancel it first with `.cancel`")
    
    # Parse arguments
    args = message.text.split()
    
    if len(args) < 3:
        return await message.reply_text(
            "❌ **Usage:** `.trade @user <waifu_id>`\n"
            "Example: `.trade @username 5`"
        )
    
    # Get target user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        waifu_id = args[1] if len(args) >= 2 else None
    else:
        try:
            target_user = await client.get_users(args[1])
            waifu_id = args[2] if len(args) >= 3 else None
        except:
            return await message.reply_text("❌ User not found!")
    
    if not waifu_id:
        return await message.reply_text("❌ Please provide waifu ID to trade!")
    
    target_id = target_user.id
    
    # Validations
    if target_id == user_id:
        return await message.reply_text("❌ You can't trade with yourself!")
    
    if target_user.is_bot:
        return await message.reply_text("❌ You can't trade with bots!")
    
    try:
        waifu_id = int(waifu_id)
    except:
        return await message.reply_text("❌ Invalid waifu ID!")
    
    # Check if user owns this waifu
    user_data = await db.get_user(user_id)
    user_collection = user_data.get("collection", [])
    
    user_waifu = None
    for w in user_collection:
        if w.get("id") == waifu_id:
            user_waifu = w
            break
    
    if not user_waifu:
        return await message.reply_text("❌ You don't own a waifu with this ID!")
    
    # Check target user exists in db
    target_data = await db.get_user(target_id)
    target_collection = target_data.get("collection", [])
    
    if not target_collection:
        return await message.reply_text("❌ Target user has no waifus to trade!")
    
    # Create trade request
    trade_id = f"{user_id}_{target_id}"
    active_trades[user_id] = {
        "trade_id": trade_id,
        "sender_id": user_id,
        "sender_name": message.from_user.first_name,
        "receiver_id": target_id,
        "receiver_name": target_user.first_name,
        "sender_waifu": user_waifu,
        "receiver_waifu": None,
        "sender_confirmed": False,
        "receiver_confirmed": False,
        "status": "pending",
        "chat_id": message.chat.id
    }
    
    # Create buttons for target to select waifu
    buttons = [
        [
            InlineKeyboardButton("✅ Accept Trade", callback_data=f"trade_accept_{user_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"trade_decline_{user_id}")
        ]
    ]
    
    await message.reply_text(
        f"📤 **Trade Request Sent!**\n\n"
        f"**From:** {message.from_user.mention}\n"
        f"**To:** {target_user.mention}\n\n"
        f"**Offering:** {user_waifu['name']} ({user_waifu['rarity']})\n"
        f"**Anime:** {user_waifu.get('anime', 'Unknown')}\n\n"
        f"⏳ Waiting for {target_user.first_name} to respond...",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^trade_accept_(\d+)$"))
async def accept_trade_callback(client: Client, callback: CallbackQuery):
    """Accept trade and select waifu to offer"""
    sender_id = int(callback.matches[0].group(1))
    receiver_id = callback.from_user.id
    
    if sender_id not in active_trades:
        return await callback.answer("❌ Trade expired!", show_alert=True)
    
    trade = active_trades[sender_id]
    
    if trade["receiver_id"] != receiver_id:
        return await callback.answer("❌ This trade is not for you!", show_alert=True)
    
    # Get receiver's collection
    receiver_data = await db.get_user(receiver_id)
    collection = receiver_data.get("collection", [])
    
    if not collection:
        await callback.answer("❌ You have no waifus!", show_alert=True)
        del active_trades[sender_id]
        return
    
    # Show first 8 waifus to select
    buttons = []
    row = []
    for i, waifu in enumerate(collection[:8]):
        row.append(
            InlineKeyboardButton(
                f"{waifu['name'][:10]}",
                callback_data=f"trade_select_{sender_id}_{waifu['id']}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{sender_id}")])
    
    await callback.message.edit_text(
        f"🔄 **Select Your Waifu to Trade**\n\n"
        f"**You're receiving:** {trade['sender_waifu']['name']}\n"
        f"**From:** {trade['sender_name']}\n\n"
        f"Select a waifu to offer:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^trade_select_(\d+)_(\d+)$"))
async def select_waifu_callback(client: Client, callback: CallbackQuery):
    """Select waifu for trade"""
    sender_id = int(callback.matches[0].group(1))
    waifu_id = int(callback.matches[0].group(2))
    receiver_id = callback.from_user.id
    
    if sender_id not in active_trades:
        return await callback.answer("❌ Trade expired!", show_alert=True)
    
    trade = active_trades[sender_id]
    
    if trade["receiver_id"] != receiver_id:
        return await callback.answer("❌ This trade is not for you!", show_alert=True)
    
    # Get receiver's waifu
    receiver_data = await db.get_user(receiver_id)
    collection = receiver_data.get("collection", [])
    
    receiver_waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            receiver_waifu = w
            break
    
    if not receiver_waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)
    
    # Update trade
    trade["receiver_waifu"] = receiver_waifu
    trade["status"] = "confirming"
    
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm Trade", callback_data=f"trade_confirm_{sender_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{sender_id}")
        ]
    ]
    
    await callback.message.edit_text(
        f"🔄 **Trade Confirmation**\n\n"
        f"**{trade['sender_name']}** offers:\n"
        f"└ {trade['sender_waifu']['name']} ({trade['sender_waifu']['rarity']})\n\n"
        f"**{trade['receiver_name']}** offers:\n"
        f"└ {receiver_waifu['name']} ({receiver_waifu['rarity']})\n\n"
        f"Both parties must confirm to complete trade!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer("Waifu selected! Now confirm the trade.")


@Client.on_callback_query(filters.regex(r"^trade_confirm_(\d+)$"))
async def confirm_trade_callback(client: Client, callback: CallbackQuery):
    """Confirm trade"""
    sender_id = int(callback.matches[0].group(1))
    user_id = callback.from_user.id
    
    if sender_id not in active_trades:
        return await callback.answer("❌ Trade expired!", show_alert=True)
    
    trade = active_trades[sender_id]
    
    if user_id not in [trade["sender_id"], trade["receiver_id"]]:
        return await callback.answer("❌ Not your trade!", show_alert=True)
    
    if trade["status"] != "confirming":
        return await callback.answer("❌ Trade not ready!", show_alert=True)
    
    # Mark confirmation
    if user_id == trade["sender_id"]:
        if trade["sender_confirmed"]:
            return await callback.answer("✅ Already confirmed!", show_alert=True)
        trade["sender_confirmed"] = True
        await callback.answer("✅ You confirmed! Waiting for other party...")
    else:
        if trade["receiver_confirmed"]:
            return await callback.answer("✅ Already confirmed!", show_alert=True)
        trade["receiver_confirmed"] = True
        await callback.answer("✅ You confirmed! Waiting for other party...")
    
    # Check if both confirmed
    if trade["sender_confirmed"] and trade["receiver_confirmed"]:
        # Execute trade
        try:
            # Remove waifus from original owners
            await db.remove_from_collection(trade["sender_id"], trade["sender_waifu"]["id"])
            await db.remove_from_collection(trade["receiver_id"], trade["receiver_waifu"]["id"])
            
            # Add to new owners
            await db.add_to_collection(trade["sender_id"], trade["receiver_waifu"])
            await db.add_to_collection(trade["receiver_id"], trade["sender_waifu"])
            
            # Clean up
            del active_trades[sender_id]
            
            await callback.message.edit_text(
                f"✅ **Trade Completed!**\n\n"
                f"**{trade['sender_name']}** received:\n"
                f"└ {trade['receiver_waifu']['name']}\n\n"
                f"**{trade['receiver_name']}** received:\n"
                f"└ {trade['sender_waifu']['name']}\n\n"
                f"🎉 Happy collecting!"
            )
        except Exception as e:
            await callback.message.edit_text(f"❌ Trade failed: {str(e)}")
            if sender_id in active_trades:
                del active_trades[sender_id]
    else:
        # Update message to show who confirmed
        sender_status = "✅" if trade["sender_confirmed"] else "⏳"
        receiver_status = "✅" if trade["receiver_confirmed"] else "⏳"
        
        buttons = [
            [
                InlineKeyboardButton("✅ Confirm Trade", callback_data=f"trade_confirm_{sender_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"trade_decline_{sender_id}")
            ]
        ]
        
        await callback.message.edit_text(
            f"🔄 **Trade Confirmation**\n\n"
            f"**{trade['sender_name']}** offers:\n"
            f"└ {trade['sender_waifu']['name']} ({trade['sender_waifu']['rarity']}) {sender_status}\n\n"
            f"**{trade['receiver_name']}** offers:\n"
            f"└ {trade['receiver_waifu']['name']} ({trade['receiver_waifu']['rarity']}) {receiver_status}\n\n"
            f"Both parties must confirm to complete trade!",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


@Client.on_callback_query(filters.regex(r"^trade_decline_(\d+)$"))
async def decline_trade_callback(client: Client, callback: CallbackQuery):
    """Decline or cancel trade"""
    sender_id = int(callback.matches[0].group(1))
    user_id = callback.from_user.id
    
    if sender_id not in active_trades:
        return await callback.answer("❌ Trade already expired!", show_alert=True)
    
    trade = active_trades[sender_id]
    
    if user_id not in [trade["sender_id"], trade["receiver_id"]]:
        return await callback.answer("❌ Not your trade!", show_alert=True)
    
    del active_trades[sender_id]
    
    decliner = "Sender" if user_id == trade["sender_id"] else "Receiver"
    
    await callback.message.edit_text(
        f"❌ **Trade Cancelled**\n\n"
        f"{decliner} cancelled the trade."
    )
    await callback.answer("Trade cancelled!")


@Client.on_message(filters.command(["cancel", "canceltrade"], prefixes=COMMAND_PREFIX))
async def cancel_trade_cmd(client: Client, message: Message):
    """Cancel active trade"""
    user_id = message.from_user.id
    
    if user_id not in active_trades:
        return await message.reply_text("❌ You don't have any active trade!")
    
    del active_trades[user_id]
    await message.reply_text("✅ Trade cancelled successfully!")


@Client.on_message(filters.command(["mytrades", "trades"], prefixes=COMMAND_PREFIX))
async def my_trades_cmd(client: Client, message: Message):
    """View pending trades"""
    user_id = message.from_user.id
    
    user_trades = []
    
    for sender_id, trade in active_trades.items():
        if trade["sender_id"] == user_id or trade["receiver_id"] == user_id:
            role = "Sender" if trade["sender_id"] == user_id else "Receiver"
            user_trades.append({
                "trade": trade,
                "role": role
            })
    
    if not user_trades:
        return await message.reply_text("📭 You have no pending trades!")
    
    text = "📋 **Your Pending Trades**\n\n"
    
    for i, t in enumerate(user_trades, 1):
        trade = t["trade"]
        text += (
            f"**{i}.** {trade['sender_name']} ↔️ {trade['receiver_name']}\n"
            f"   Status: {trade['status'].title()}\n"
            f"   Your role: {t['role']}\n\n"
        )
    
    await message.reply_text(text)