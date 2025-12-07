from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database import db
import config
import asyncio
import random
from datetime import datetime, timedelta

__MODULE__ = "Trade"
__HELP__ = """
🔄 **Waifu Trade System**

**Commands:**
• `.trade @user` - Start trade with user
• `.mytrades` - View your pending trades
• `.cancel` - Cancel your trade request

**How it works:**
1. Initiate trade with `.trade @user`
2. Select waifu to offer
3. Other user selects their waifu
4. Both confirm to complete trade

**Features:**
✨ Sexy trade interface
💖 Emotional confirmation messages
🎁 Special trade bonuses
🔒 Secure trade system
"""

# Active trades storage with expiration
active_trades = {}

# Trade cooldowns to prevent spam
trade_cooldowns = {}

async def get_user_name(client: Client, user_id: int) -> str:
    """Get user's display name"""
    try:
        user = await client.get_users(user_id)
        return user.first_name or user.username or f"User {user_id}"
    except:
        return f"User {user_id}"

async def get_waifu_info(waifu_data: dict) -> str:
    """Format waifu info for display"""
    rarity_emoji = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(waifu_data.get("rarity", "common").lower(), "⚪")

    return (
        f"{rarity_emoji} **{waifu_data.get('name', 'Unknown')}**\n"
        f"📺 {waifu_data.get('anime', 'Unknown')}\n"
        f"⚔️ {waifu_data.get('power', 0)} | "
        f"💎 {waifu_data.get('rarity', 'common').title()}"
    )

def setup(app: Client):
    """Setup trade module with sexy UI"""

    @app.on_message(filters.command(["trade", "tr"], prefixes=config.COMMAND_PREFIX))
    async def trade_start(client: Client, message: Message):
        """Initiate a sexy trade with another user"""
        user_id = message.from_user.id

        # Check cooldown
        if user_id in trade_cooldowns:
            remaining = (trade_cooldowns[user_id] - datetime.now()).total_seconds()
            if remaining > 0:
                return await message.reply_text(
                    f"⏳ You're trading too fast! Wait {int(remaining)} seconds."
                )

        # Parse arguments
        if not message.reply_to_message and len(message.command) < 2:
            return await message.reply_text(
                "❌ **Usage:** Reply to a user or use `.trade @username`"
            )

        # Get target user
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
        else:
            try:
                target_user = await client.get_users(message.command[1])
            except:
                return await message.reply_text("❌ User not found!")

        target_id = target_user.id

        # Validations
        if target_id == user_id:
            return await message.reply_text("❌ You can't trade with yourself, sweetheart!")

        if target_user.is_bot:
            return await message.reply_text("❌ Bots can't trade waifus, baby!")

        # Check if user already has active trade
        if user_id in active_trades:
            return await message.reply_text(
                "❌ You already have an active trade! Cancel it first with `.cancel`"
            )

        # Get user's collection
        user_data = await db.get_user(user_id)
        user_collection = user_data.get("collection", [])

        if not user_collection:
            return await message.reply_text(
                "❌ You don't have any waifus to trade, baby! Collect some first!"
            )

        # Create trade request
        trade_id = f"{user_id}_{target_id}_{datetime.now().timestamp()}"
        active_trades[trade_id] = {
            "trade_id": trade_id,
            "sender_id": user_id,
            "sender_name": message.from_user.first_name,
            "receiver_id": target_id,
            "receiver_name": target_user.first_name,
            "sender_waifu": None,
            "receiver_waifu": None,
            "sender_confirmed": False,
            "receiver_confirmed": False,
            "status": "pending",
            "created_at": datetime.now(),
            "chat_id": message.chat.id,
            "message_id": None
        }

        # Create waifu selection buttons
        buttons = []
        row = []
        for i, waifu in enumerate(user_collection[:12]):  # Show first 12 waifus
            row.append(
                InlineKeyboardButton(
                    f"{waifu.get('name', 'Unknown')[:12]}",
                    callback_data=f"select_waifu_{trade_id}_{waifu.get('id')}"
                )
            )
            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_trade_{trade_id}")
        ])

        # Send trade initiation message
        sent = await message.reply_text(
            f"💘 **New Trade Request!**\n\n"
            f"**From:** {message.from_user.mention}\n"
            f"**To:** {target_user.mention}\n\n"
            f"Select a waifu to offer in trade:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        active_trades[trade_id]["message_id"] = sent.id

        # Set cooldown
        trade_cooldowns[user_id] = datetime.now() + timedelta(minutes=1)

    @app.on_callback_query(filters.regex(r"^select_waifu_(.+?)_(\d+)$"))
    async def select_waifu_callback(client: Client, callback: CallbackQuery):
        """Select waifu to offer in trade"""
        trade_id, waifu_id = callback.matches[0].group(1), int(callback.matches[0].group(2))
        user_id = callback.from_user.id

        if trade_id not in active_trades:
            return await callback.answer("❌ Trade expired!", show_alert=True)

        trade = active_trades[trade_id]

        if trade["sender_id"] != user_id:
            return await callback.answer("❌ This trade isn't yours!", show_alert=True)

        if trade["status"] != "pending":
            return await callback.answer("❌ Trade already in progress!", show_alert=True)

        # Get user's collection
        user_data = await db.get_user(user_id)
        user_collection = user_data.get("collection", [])

        # Find selected waifu
        selected_waifu = None
        for waifu in user_collection:
            if waifu.get("id") == waifu_id:
                selected_waifu = waifu
                break

        if not selected_waifu:
            return await callback.answer("❌ Waifu not found!", show_alert=True)

        # Update trade with selected waifu
        trade["sender_waifu"] = selected_waifu
        trade["status"] = "waiting_for_receiver"

        # Notify target user
        target_id = trade["receiver_id"]
        target_user = await client.get_users(target_id)

        # Create buttons for target to select waifu
        target_buttons = []
        row = []
        target_data = await db.get_user(target_id)
        target_collection = target_data.get("collection", [])

        if not target_collection:
            await callback.message.edit_text(
                f"❌ **Trade Failed**\n\n"
                f"{target_user.first_name} has no waifus to trade!"
            )
            del active_trades[trade_id]
            return await callback.answer("Trade cancelled!", show_alert=True)

        for i, waifu in enumerate(target_collection[:12]):  # Show first 12 waifus
            row.append(
                InlineKeyboardButton(
                    f"{waifu.get('name', 'Unknown')[:12]}",
                    callback_data=f"receiver_select_{trade_id}_{waifu.get('id')}"
                )
            )
            if len(row) == 2:
                target_buttons.append(row)
                row = []

        if row:
            target_buttons.append(row)

        target_buttons.append([
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_trade_{trade_id}")
        ])

        # Send message to target user
        try:
            await client.send_message(
                target_id,
                f"💘 **Trade Request from {trade['sender_name']}**\n\n"
                f"They're offering:\n{await get_waifu_info(selected_waifu)}\n\n"
                f"Select a waifu to offer in return:",
                reply_markup=InlineKeyboardMarkup(target_buttons)
            )

            # Update original message
            await callback.message.edit_text(
                f"💘 **Trade Request Sent!**\n\n"
                f"**To:** {target_user.mention}\n\n"
                f"You offered:\n{await get_waifu_info(selected_waifu)}\n\n"
                f"⏳ Waiting for {target_user.first_name} to respond...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel Trade", callback_data=f"cancel_trade_{trade_id}")]
                ])
            )
        except Exception as e:
            await callback.message.edit_text(f"❌ Failed to send trade request: {e}")
            del active_trades[trade_id]

        await callback.answer("Waifu selected! Waiting for response...")

    @app.on_callback_query(filters.regex(r"^receiver_select_(.+?)_(\d+)$"))
    async def receiver_select_callback(client: Client, callback: CallbackQuery):
        """Receiver selects their waifu to trade"""
        trade_id, waifu_id = callback.matches[0].group(1), int(callback.matches[0].group(2))
        user_id = callback.from_user.id

        if trade_id not in active_trades:
            return await callback.answer("❌ Trade expired!", show_alert=True)

        trade = active_trades[trade_id]

        if trade["receiver_id"] != user_id:
            return await callback.answer("❌ This trade isn't for you!", show_alert=True)

        if trade["status"] != "waiting_for_receiver":
            return await callback.answer("❌ Trade already in progress!", show_alert=True)

        # Get receiver's collection
        receiver_data = await db.get_user(user_id)
        receiver_collection = receiver_data.get("collection", [])

        # Find selected waifu
        selected_waifu = None
        for waifu in receiver_collection:
            if waifu.get("id") == waifu_id:
                selected_waifu = waifu
                break

        if not selected_waifu:
            return await callback.answer("❌ Waifu not found!", show_alert=True)

        # Update trade with receiver's waifu
        trade["receiver_waifu"] = selected_waifu
        trade["status"] = "confirming"

        # Create confirmation buttons
        buttons = [
            [
                InlineKeyboardButton("✅ Confirm Trade", callback_data=f"confirm_trade_{trade_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"decline_trade_{trade_id}")
            ]
        ]

        # Update message for both users
        sender_info = await get_waifu_info(trade["sender_waifu"])
        receiver_info = await get_waifu_info(selected_waifu)

        # For sender
        try:
            await client.edit_message_text(
                chat_id=trade["chat_id"],
                message_id=trade["message_id"],
                text=(
                    f"💘 **Trade Ready for Confirmation!**\n\n"
                    f"**{trade['sender_name']}** offers:\n{sender_info}\n\n"
                    f"**{trade['receiver_name']}** offers:\n{receiver_info}\n\n"
                    f"Both parties must confirm to complete trade!"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            pass

        # For receiver
        try:
            await callback.message.edit_text(
                f"💘 **Trade Ready for Confirmation!**\n\n"
                f"**{trade['sender_name']}** offers:\n{sender_info}\n\n"
                f"**You** offer:\n{receiver_info}\n\n"
                f"Both parties must confirm to complete trade!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            await callback.answer(f"Error: {e}", show_alert=True)

        await callback.answer("Waifu selected! Now confirm the trade.")

    @app.on_callback_query(filters.regex(r"^confirm_trade_(.+?)$"))
    async def confirm_trade_callback(client: Client, callback: CallbackQuery):
        """Confirm trade"""
        trade_id = callback.matches[0].group(1)
        user_id = callback.from_user.id

        if trade_id not in active_trades:
            return await callback.answer("❌ Trade expired!", show_alert=True)

        trade = active_trades[trade_id]

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

                # Generate sexy completion message
                sender_waifu = trade["receiver_waifu"]
                receiver_waifu = trade["sender_waifu"]

                completion_text = (
                    f"🎉 **Trade Completed!** 🎉\n\n"
                    f"💘 **{trade['sender_name']}** received:\n{await get_waifu_info(sender_waifu)}\n\n"
                    f"💘 **{trade['receiver_name']}** received:\n{await get_waifu_info(receiver_waifu)}\n\n"
                    f"Enjoy your new waifus! 💖"
                )

                # Send completion message to both parties
                try:
                    await client.send_message(
                        trade["sender_id"],
                        completion_text
                    )
                except:
                    pass

                try:
                    await client.send_message(
                        trade["receiver_id"],
                        completion_text
                    )
                except:
                    pass

                # Update original message
                try:
                    await client.edit_message_text(
                        chat_id=trade["chat_id"],
                        message_id=trade["message_id"],
                        text=completion_text
                    )
                except:
                    pass

                # Clean up
                del active_trades[trade_id]

                # Add small cooldown
                trade_cooldowns[trade["sender_id"]] = datetime.now() + timedelta(minutes=1)
                trade_cooldowns[trade["receiver_id"]] = datetime.now() + timedelta(minutes=1)

            except Exception as e:
                error_text = f"❌ **Trade Failed**: {str(e)}"
                try:
                    await client.edit_message_text(
                        chat_id=trade["chat_id"],
                        message_id=trade["message_id"],
                        text=error_text
                    )
                except:
                    pass
                del active_trades[trade_id]
        else:
            # Update message to show who confirmed
            sender_status = "✅" if trade["sender_confirmed"] else "⏳"
            receiver_status = "✅" if trade["receiver_confirmed"] else "⏳"

            sender_info = await get_waifu_info(trade["sender_waifu"])
            receiver_info = await get_waifu_info(trade["receiver_waifu"])

            try:
                await client.edit_message_text(
                    chat_id=trade["chat_id"],
                    message_id=trade["message_id"],
                    text=(
                        f"💘 **Trade Confirmation**\n\n"
                        f"**{trade['sender_name']}** offers:\n{sender_info} {sender_status}\n\n"
                        f"**{trade['receiver_name']}** offers:\n{receiver_info} {receiver_status}\n\n"
                        f"Both parties must confirm to complete trade!"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Confirm Trade", callback_data=f"confirm_trade_{trade_id}"),
                            InlineKeyboardButton("❌ Cancel", callback_data=f"decline_trade_{trade_id}")
                        ]
                    ])
                )
            except:
                pass

    @app.on_callback_query(filters.regex(r"^(decline|cancel)_trade_(.+?)$"))
    async def decline_trade_callback(client: Client, callback: CallbackQuery):
        """Decline or cancel trade"""
        action, trade_id = callback.matches[0].group(1), callback.matches[0].group(2)
        user_id = callback.from_user.id

        if trade_id not in active_trades:
            return await callback.answer("❌ Trade already expired!", show_alert=True)

        trade = active_trades[trade_id]

        if user_id not in [trade["sender_id"], trade["receiver_id"]]:
            return await callback.answer("❌ Not your trade!", show_alert=True)

        # Determine who cancelled
        canceller = "Sender" if user_id == trade["sender_id"] else "Receiver"

        # Notify both parties
        try:
            await client.edit_message_text(
                chat_id=trade["chat_id"],
                message_id=trade["message_id"],
                text=f"❌ **Trade Cancelled**\n\n{canceller} cancelled the trade."
            )
        except:
            pass

        # Notify receiver if they haven't responded yet
        if trade["status"] == "waiting_for_receiver" and user_id == trade["sender_id"]:
            try:
                target_user = await client.get_users(trade["receiver_id"])
                await client.send_message(
                    trade["receiver_id"],
                    f"❌ **Trade Cancelled**\n\n{trade['sender_name']} cancelled the trade."
                )
            except:
                pass

        # Clean up
        del active_trades[trade_id]
        await callback.answer("Trade cancelled!", show_alert=True)

    @app.on_message(filters.command(["mytrades", "trades"], prefixes=config.COMMAND_PREFIX))
    async def my_trades_cmd(client: Client, message: Message):
        """View pending trades"""
        user_id = message.from_user.id
        user_trades = []

        for trade_id, trade in active_trades.items():
            if trade["sender_id"] == user_id or trade["receiver_id"] == user_id:
                role = "Sender" if trade["sender_id"] == user_id else "Receiver"
                status_emoji = {
                    "pending": "⏳",
                    "waiting_for_receiver": "📤",
                    "confirming": "✅"
                }.get(trade["status"], "❓")

                user_trades.append({
                    "trade_id": trade_id,
                    "role": role,
                    "status": trade["status"],
                    "status_emoji": status_emoji,
                    "other_user": trade["receiver_name"] if role == "Sender" else trade["sender_name"]
                })

        if not user_trades:
            return await message.reply_text("📭 You have no pending trades!")

        text = "📋 **Your Pending Trades**\n\n"
        for i, trade in enumerate(user_trades, 1):
            text += (
                f"**{i}.** {trade['status_emoji']} {trade['other_user']}\n"
                f"   Role: {trade['role']}\n"
                f"   Status: {trade['status'].title()}\n\n"
            )

        await message.reply_text(text)

    @app.on_message(filters.command(["cancel", "canceltrade"], prefixes=config.COMMAND_PREFIX))
    async def cancel_trade_cmd(client: Client, message: Message):
        """Cancel active trade"""
        user_id = message.from_user.id
        cancelled = False

        # Find and cancel user's trade
        for trade_id, trade in list(active_trades.items()):
            if trade["sender_id"] == user_id or trade["receiver_id"] == user_id:
                # Determine who cancelled
                canceller = "Sender" if trade["sender_id"] == user_id else "Receiver"

                # Notify in chat if possible
                try:
                    await client.edit_message_text(
                        chat_id=trade["chat_id"],
                        message_id=trade["message_id"],
                        text=f"❌ **Trade Cancelled**\n\n{canceller} cancelled the trade."
                    )
                except:
                    pass

                # Notify other party if they haven't responded
                if trade["status"] == "waiting_for_receiver" and trade["sender_id"] == user_id:
                    try:
                        target_user = await client.get_users(trade["receiver_id"])
                        await client.send_message(
                            trade["receiver_id"],
                            f"❌ **Trade Cancelled**\n\n{trade['sender_name']} cancelled the trade."
                        )
                    except:
                        pass

                del active_trades[trade_id]
                cancelled = True

        if cancelled:
            await message.reply_text("✅ All your trades have been cancelled!")
        else:
            await message.reply_text("📭 You have no active trades to cancel.")
