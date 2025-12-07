# modules/trade.py - Sexy Waifu Trade System with Debugging

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
import asyncio
import random
from datetime import datetime, timedelta
import traceback

# Debug mode - set to True for detailed logging
DEBUG_MODE = True

def debug_log(message: str):
    """Print debug messages if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[TRADE DEBUG] {datetime.now().strftime('%H:%M:%S')} - {message}")

__MODULE__ = "Trade"
__HELP__ = """
🔄 **Waifu Trade System**

**Commands:**
• `/trade @user` - Start trade with user
• `/mytrades` - View your pending trades
• `/canceltrade` - Cancel your trade request

**How it works:**
1. Initiate trade with `/trade @user`
2. Select waifu to offer
3. Other user selects their waifu
4. Both confirm to complete trade
"""

# Active trades storage with expiration
active_trades = {}

# Trade cooldowns to prevent spam
trade_cooldowns = {}

# Try to import database - with fallback for debugging
try:
    from database import db
    debug_log("Database module imported successfully")
except ImportError as e:
    debug_log(f"Database import error: {e}")
    # Create a mock database for testing
    class MockDB:
        async def get_user(self, user_id):
            debug_log(f"MockDB: get_user({user_id})")
            return {"collection": []}
        
        async def add_to_collection(self, user_id, waifu):
            debug_log(f"MockDB: add_to_collection({user_id}, {waifu})")
            return True
        
        async def remove_from_collection(self, user_id, waifu_id):
            debug_log(f"MockDB: remove_from_collection({user_id}, {waifu_id})")
            return True
    
    db = MockDB()

# Try to import config - with fallback
try:
    import config
    COMMAND_PREFIX = getattr(config, 'COMMAND_PREFIX', ['/', '.', '!'])
    debug_log(f"Config imported, prefix: {COMMAND_PREFIX}")
except ImportError:
    COMMAND_PREFIX = ['/', '.', '!']
    debug_log(f"Using default prefix: {COMMAND_PREFIX}")


async def get_user_name(client: Client, user_id: int) -> str:
    """Get user's display name"""
    try:
        user = await client.get_users(user_id)
        name = user.first_name or user.username or f"User {user_id}"
        debug_log(f"get_user_name({user_id}) = {name}")
        return name
    except Exception as e:
        debug_log(f"get_user_name error: {e}")
        return f"User {user_id}"


async def get_waifu_info(waifu_data: dict) -> str:
    """Format waifu info for display"""
    debug_log(f"get_waifu_info: {waifu_data}")
    
    if not waifu_data:
        return "❓ Unknown Waifu"
    
    rarity_emoji = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(waifu_data.get("rarity", "common")).lower(), "⚪")

    return (
        f"{rarity_emoji} **{waifu_data.get('name', 'Unknown')}**\n"
        f"📺 {waifu_data.get('anime', 'Unknown')}\n"
        f"⚔️ Power: {waifu_data.get('power', 0)} | "
        f"💎 {str(waifu_data.get('rarity', 'common')).title()}"
    )


async def get_user_collection(user_id: int) -> list:
    """Safely get user's waifu collection"""
    try:
        user_data = await db.get_user(user_id)
        debug_log(f"User data for {user_id}: {type(user_data)}")
        
        if user_data is None:
            debug_log(f"User {user_id} not found in database")
            return []
        
        collection = user_data.get("collection", [])
        debug_log(f"Collection for {user_id}: {len(collection)} waifus")
        return collection
    except Exception as e:
        debug_log(f"Error getting collection for {user_id}: {e}")
        traceback.print_exc()
        return []


def generate_trade_id(sender_id: int, receiver_id: int) -> str:
    """Generate unique trade ID"""
    trade_id = f"t{sender_id}{receiver_id}{int(datetime.now().timestamp())}"
    debug_log(f"Generated trade_id: {trade_id}")
    return trade_id


def setup(app: Client):
    """Setup trade module with sexy UI"""
    debug_log("Setting up trade module...")

    @app.on_message(filters.command(["trade", "tr"]))
    async def trade_start(client: Client, message: Message):
        """Initiate a sexy trade with another user"""
        debug_log(f"Trade command received from {message.from_user.id}")
        debug_log(f"Message text: {message.text}")
        debug_log(f"Command args: {message.command}")
        
        try:
            user_id = message.from_user.id

            # Check cooldown
            if user_id in trade_cooldowns:
                remaining = (trade_cooldowns[user_id] - datetime.now()).total_seconds()
                if remaining > 0:
                    debug_log(f"User {user_id} on cooldown: {remaining}s")
                    return await message.reply_text(
                        f"⏳ You're trading too fast! Wait {int(remaining)} seconds."
                    )

            # Parse target user
            target_user = None
            
            # Method 1: Reply to message
            if message.reply_to_message:
                target_user = message.reply_to_message.from_user
                debug_log(f"Target from reply: {target_user.id if target_user else None}")
            
            # Method 2: Username/ID in command
            elif len(message.command) >= 2:
                try:
                    target_input = message.command[1]
                    debug_log(f"Target input: {target_input}")
                    target_user = await client.get_users(target_input)
                    debug_log(f"Target from command: {target_user.id if target_user else None}")
                except Exception as e:
                    debug_log(f"Error getting target user: {e}")
                    return await message.reply_text(
                        f"❌ User not found! Error: {e}"
                    )
            else:
                return await message.reply_text(
                    "❌ **Usage:** Reply to a user or use `/trade @username`"
                )

            if not target_user:
                return await message.reply_text("❌ Could not find the target user!")

            target_id = target_user.id
            debug_log(f"Target ID: {target_id}")

            # Validations
            if target_id == user_id:
                debug_log("User tried to trade with themselves")
                return await message.reply_text("❌ You can't trade with yourself!")

            if target_user.is_bot:
                debug_log("User tried to trade with a bot")
                return await message.reply_text("❌ Bots can't trade waifus!")

            # Check if user already has active trade
            for tid, trade in active_trades.items():
                if trade["sender_id"] == user_id:
                    debug_log(f"User {user_id} already has active trade: {tid}")
                    return await message.reply_text(
                        "❌ You already have an active trade! Cancel it first with `/canceltrade`"
                    )

            # Get user's collection
            user_collection = await get_user_collection(user_id)
            debug_log(f"User collection count: {len(user_collection)}")

            if not user_collection:
                # For testing, create dummy waifus
                if DEBUG_MODE:
                    debug_log("Creating dummy waifus for testing")
                    user_collection = [
                        {"id": 1, "name": "Test Waifu 1", "anime": "Test Anime", "rarity": "common", "power": 100},
                        {"id": 2, "name": "Test Waifu 2", "anime": "Test Anime", "rarity": "rare", "power": 200},
                        {"id": 3, "name": "Test Waifu 3", "anime": "Test Anime", "rarity": "epic", "power": 300},
                    ]
                else:
                    return await message.reply_text(
                        "❌ You don't have any waifus to trade! Collect some first!"
                    )

            # Create trade request
            trade_id = generate_trade_id(user_id, target_id)
            
            active_trades[trade_id] = {
                "trade_id": trade_id,
                "sender_id": user_id,
                "sender_name": message.from_user.first_name or "User",
                "receiver_id": target_id,
                "receiver_name": target_user.first_name or "User",
                "sender_waifu": None,
                "receiver_waifu": None,
                "sender_confirmed": False,
                "receiver_confirmed": False,
                "status": "pending",
                "created_at": datetime.now(),
                "chat_id": message.chat.id,
                "message_id": None
            }
            
            debug_log(f"Created trade: {trade_id}")
            debug_log(f"Active trades count: {len(active_trades)}")

            # Create waifu selection buttons
            buttons = []
            row = []
            
            for i, waifu in enumerate(user_collection[:12]):
                waifu_id = waifu.get("id", i)
                waifu_name = waifu.get("name", f"Waifu {i}")[:15]
                callback_data = f"selw_{trade_id}_{waifu_id}"
                
                debug_log(f"Button {i}: {waifu_name} -> {callback_data}")
                
                row.append(
                    InlineKeyboardButton(
                        waifu_name,
                        callback_data=callback_data
                    )
                )
                
                if len(row) == 2:
                    buttons.append(row)
                    row = []

            if row:
                buttons.append(row)

            buttons.append([
                InlineKeyboardButton("❌ Cancel", callback_data=f"cncl_{trade_id}")
            ])

            debug_log(f"Created {len(buttons)} button rows")

            # Send trade initiation message
            sent = await message.reply_text(
                f"💘 **New Trade Request!**\n\n"
                f"**From:** {message.from_user.mention}\n"
                f"**To:** {target_user.mention}\n\n"
                f"📦 Select a waifu to offer in trade:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            active_trades[trade_id]["message_id"] = sent.id
            debug_log(f"Sent message ID: {sent.id}")

            # Set cooldown
            trade_cooldowns[user_id] = datetime.now() + timedelta(seconds=30)

        except Exception as e:
            debug_log(f"Error in trade_start: {e}")
            traceback.print_exc()
            await message.reply_text(f"❌ Error starting trade: {e}")

    @app.on_callback_query(filters.regex(r"^selw_(.+)_(\d+)$"))
    async def select_waifu_callback(client: Client, callback: CallbackQuery):
        """Sender selects waifu to offer"""
        debug_log(f"select_waifu_callback triggered")
        debug_log(f"Callback data: {callback.data}")
        debug_log(f"User: {callback.from_user.id}")
        
        try:
            match = callback.matches[0]
            trade_id = match.group(1)
            waifu_id = int(match.group(2))
            user_id = callback.from_user.id

            debug_log(f"Parsed - trade_id: {trade_id}, waifu_id: {waifu_id}")

            if trade_id not in active_trades:
                debug_log(f"Trade {trade_id} not found in active_trades")
                debug_log(f"Active trades: {list(active_trades.keys())}")
                return await callback.answer("❌ Trade expired!", show_alert=True)

            trade = active_trades[trade_id]
            debug_log(f"Found trade: {trade['status']}")

            if trade["sender_id"] != user_id:
                debug_log(f"Wrong user. Expected: {trade['sender_id']}, Got: {user_id}")
                return await callback.answer("❌ This trade isn't yours!", show_alert=True)

            if trade["status"] != "pending":
                debug_log(f"Wrong status: {trade['status']}")
                return await callback.answer("❌ Trade already in progress!", show_alert=True)

            # Get user's collection
            user_collection = await get_user_collection(user_id)
            
            # For testing
            if not user_collection and DEBUG_MODE:
                user_collection = [
                    {"id": 1, "name": "Test Waifu 1", "anime": "Test Anime", "rarity": "common", "power": 100},
                    {"id": 2, "name": "Test Waifu 2", "anime": "Test Anime", "rarity": "rare", "power": 200},
                    {"id": 3, "name": "Test Waifu 3", "anime": "Test Anime", "rarity": "epic", "power": 300},
                ]

            # Find selected waifu
            selected_waifu = None
            for waifu in user_collection:
                if waifu.get("id") == waifu_id:
                    selected_waifu = waifu
                    break

            if not selected_waifu:
                debug_log(f"Waifu {waifu_id} not found in collection")
                return await callback.answer("❌ Waifu not found!", show_alert=True)

            debug_log(f"Selected waifu: {selected_waifu}")

            # Update trade
            trade["sender_waifu"] = selected_waifu
            trade["status"] = "waiting_receiver"

            # Get receiver's collection
            receiver_collection = await get_user_collection(trade["receiver_id"])
            
            # For testing
            if not receiver_collection and DEBUG_MODE:
                receiver_collection = [
                    {"id": 101, "name": "Recv Waifu 1", "anime": "Recv Anime", "rarity": "rare", "power": 150},
                    {"id": 102, "name": "Recv Waifu 2", "anime": "Recv Anime", "rarity": "epic", "power": 250},
                ]

            if not receiver_collection:
                await callback.message.edit_text(
                    f"❌ **Trade Failed**\n\n"
                    f"{trade['receiver_name']} has no waifus to trade!"
                )
                del active_trades[trade_id]
                return await callback.answer("Trade cancelled!")

            # Create buttons for receiver
            recv_buttons = []
            row = []
            
            for i, waifu in enumerate(receiver_collection[:12]):
                waifu_id_recv = waifu.get("id", i)
                waifu_name = waifu.get("name", f"Waifu {i}")[:15]
                callback_data = f"rsel_{trade_id}_{waifu_id_recv}"
                
                row.append(
                    InlineKeyboardButton(waifu_name, callback_data=callback_data)
                )
                
                if len(row) == 2:
                    recv_buttons.append(row)
                    row = []

            if row:
                recv_buttons.append(row)

            recv_buttons.append([
                InlineKeyboardButton("❌ Decline", callback_data=f"decl_{trade_id}")
            ])

            waifu_info = await get_waifu_info(selected_waifu)

            # Update original message
            await callback.message.edit_text(
                f"💘 **Trade in Progress**\n\n"
                f"**You offered:**\n{waifu_info}\n\n"
                f"⏳ Waiting for {trade['receiver_name']} to respond...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"cncl_{trade_id}")]
                ])
            )

            # Try to notify receiver
            try:
                await client.send_message(
                    trade["receiver_id"],
                    f"💘 **Trade Request from {trade['sender_name']}**\n\n"
                    f"They're offering:\n{waifu_info}\n\n"
                    f"Select a waifu to offer in return:",
                    reply_markup=InlineKeyboardMarkup(recv_buttons)
                )
                debug_log(f"Sent notification to receiver {trade['receiver_id']}")
            except Exception as e:
                debug_log(f"Could not DM receiver: {e}")
                # Send in group instead
                await client.send_message(
                    trade["chat_id"],
                    f"💘 **{trade['receiver_name']}**, you have a trade request!\n\n"
                    f"**{trade['sender_name']}** is offering:\n{waifu_info}\n\n"
                    f"Select a waifu to offer in return:",
                    reply_markup=InlineKeyboardMarkup(recv_buttons)
                )

            await callback.answer("✅ Waifu selected! Waiting for response...")

        except Exception as e:
            debug_log(f"Error in select_waifu_callback: {e}")
            traceback.print_exc()
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

    @app.on_callback_query(filters.regex(r"^rsel_(.+)_(\d+)$"))
    async def receiver_select_callback(client: Client, callback: CallbackQuery):
        """Receiver selects their waifu"""
        debug_log(f"receiver_select_callback triggered")
        debug_log(f"Callback data: {callback.data}")
        
        try:
            match = callback.matches[0]
            trade_id = match.group(1)
            waifu_id = int(match.group(2))
            user_id = callback.from_user.id

            if trade_id not in active_trades:
                return await callback.answer("❌ Trade expired!", show_alert=True)

            trade = active_trades[trade_id]

            if trade["receiver_id"] != user_id:
                return await callback.answer("❌ This trade isn't for you!", show_alert=True)

            if trade["status"] != "waiting_receiver":
                return await callback.answer("❌ Invalid trade state!", show_alert=True)

            # Get receiver's collection
            receiver_collection = await get_user_collection(user_id)
            
            if not receiver_collection and DEBUG_MODE:
                receiver_collection = [
                    {"id": 101, "name": "Recv Waifu 1", "anime": "Recv Anime", "rarity": "rare", "power": 150},
                    {"id": 102, "name": "Recv Waifu 2", "anime": "Recv Anime", "rarity": "epic", "power": 250},
                ]

            # Find selected waifu
            selected_waifu = None
            for waifu in receiver_collection:
                if waifu.get("id") == waifu_id:
                    selected_waifu = waifu
                    break

            if not selected_waifu:
                return await callback.answer("❌ Waifu not found!", show_alert=True)

            # Update trade
            trade["receiver_waifu"] = selected_waifu
            trade["status"] = "confirming"

            sender_info = await get_waifu_info(trade["sender_waifu"])
            receiver_info = await get_waifu_info(selected_waifu)

            confirm_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"conf_{trade_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cncl_{trade_id}")
                ]
            ])

            confirm_text = (
                f"💘 **Trade Ready for Confirmation!**\n\n"
                f"**{trade['sender_name']}** offers:\n{sender_info}\n\n"
                f"**{trade['receiver_name']}** offers:\n{receiver_info}\n\n"
                f"Both parties must click ✅ Confirm to complete!"
            )

            # Update receiver's message
            await callback.message.edit_text(confirm_text, reply_markup=confirm_buttons)

            # Notify sender
            try:
                await client.send_message(
                    trade["sender_id"],
                    confirm_text,
                    reply_markup=confirm_buttons
                )
            except Exception as e:
                debug_log(f"Could not notify sender: {e}")

            await callback.answer("✅ Now both parties need to confirm!")

        except Exception as e:
            debug_log(f"Error in receiver_select_callback: {e}")
            traceback.print_exc()
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

    @app.on_callback_query(filters.regex(r"^conf_(.+)$"))
    async def confirm_trade_callback(client: Client, callback: CallbackQuery):
        """Confirm trade"""
        debug_log(f"confirm_trade_callback triggered")
        
        try:
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
                    return await callback.answer("✅ Already confirmed!")
                trade["sender_confirmed"] = True
                await callback.answer("✅ You confirmed!")
            else:
                if trade["receiver_confirmed"]:
                    return await callback.answer("✅ Already confirmed!")
                trade["receiver_confirmed"] = True
                await callback.answer("✅ You confirmed!")

            debug_log(f"Confirmations - Sender: {trade['sender_confirmed']}, Receiver: {trade['receiver_confirmed']}")

            # Check if both confirmed
            if trade["sender_confirmed"] and trade["receiver_confirmed"]:
                debug_log("Both confirmed! Executing trade...")
                
                try:
                    # Execute trade in database
                    await db.remove_from_collection(trade["sender_id"], trade["sender_waifu"]["id"])
                    await db.remove_from_collection(trade["receiver_id"], trade["receiver_waifu"]["id"])
                    await db.add_to_collection(trade["sender_id"], trade["receiver_waifu"])
                    await db.add_to_collection(trade["receiver_id"], trade["sender_waifu"])

                    sender_info = await get_waifu_info(trade["receiver_waifu"])
                    receiver_info = await get_waifu_info(trade["sender_waifu"])

                    success_text = (
                        f"🎉 **Trade Completed!** 🎉\n\n"
                        f"💘 **{trade['sender_name']}** received:\n{sender_info}\n\n"
                        f"💘 **{trade['receiver_name']}** received:\n{receiver_info}\n\n"
                        f"Enjoy your new waifus! 💖"
                    )

                    # Update message
                    try:
                        await callback.message.edit_text(success_text)
                    except:
                        pass

                    # Notify both
                    try:
                        await client.send_message(trade["sender_id"], success_text)
                    except:
                        pass
                    
                    try:
                        await client.send_message(trade["receiver_id"], success_text)
                    except:
                        pass

                    # Cleanup
                    del active_trades[trade_id]
                    debug_log(f"Trade {trade_id} completed successfully!")

                except Exception as e:
                    debug_log(f"Error executing trade: {e}")
                    traceback.print_exc()
                    await callback.message.edit_text(f"❌ Trade failed: {e}")
                    del active_trades[trade_id]
            else:
                # Update status
                sender_info = await get_waifu_info(trade["sender_waifu"])
                receiver_info = await get_waifu_info(trade["receiver_waifu"])
                
                status_text = (
                    f"💘 **Trade Confirmation**\n\n"
                    f"**{trade['sender_name']}** offers:\n{sender_info}\n"
                    f"Status: {'✅' if trade['sender_confirmed'] else '⏳'}\n\n"
                    f"**{trade['receiver_name']}** offers:\n{receiver_info}\n"
                    f"Status: {'✅' if trade['receiver_confirmed'] else '⏳'}\n\n"
                    f"Waiting for both confirmations..."
                )

                try:
                    await callback.message.edit_text(
                        status_text,
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("✅ Confirm", callback_data=f"conf_{trade_id}"),
                                InlineKeyboardButton("❌ Cancel", callback_data=f"cncl_{trade_id}")
                            ]
                        ])
                    )
                except:
                    pass

        except Exception as e:
            debug_log(f"Error in confirm_trade_callback: {e}")
            traceback.print_exc()
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

    @app.on_callback_query(filters.regex(r"^(cncl|decl)_(.+)$"))
    async def cancel_trade_callback(client: Client, callback: CallbackQuery):
        """Cancel or decline trade"""
        debug_log(f"cancel_trade_callback triggered: {callback.data}")
        
        try:
            match = callback.matches[0]
            action = match.group(1)
            trade_id = match.group(2)
            user_id = callback.from_user.id

            if trade_id not in active_trades:
                return await callback.answer("❌ Trade already expired!", show_alert=True)

            trade = active_trades[trade_id]

            if user_id not in [trade["sender_id"], trade["receiver_id"]]:
                return await callback.answer("❌ Not your trade!", show_alert=True)

            canceller_name = callback.from_user.first_name

            cancel_text = f"❌ **Trade Cancelled**\n\n{canceller_name} cancelled the trade."

            # Update message
            try:
                await callback.message.edit_text(cancel_text)
            except:
                pass

            # Cleanup
            del active_trades[trade_id]
            debug_log(f"Trade {trade_id} cancelled by {user_id}")

            await callback.answer("Trade cancelled!", show_alert=True)

        except Exception as e:
            debug_log(f"Error in cancel_trade_callback: {e}")
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

    @app.on_message(filters.command(["mytrades", "trades"]))
    async def my_trades_cmd(client: Client, message: Message):
        """View pending trades"""
        debug_log(f"mytrades command from {message.from_user.id}")
        
        user_id = message.from_user.id
        user_trades = []

        for trade_id, trade in active_trades.items():
            if trade["sender_id"] == user_id or trade["receiver_id"] == user_id:
                role = "Sender" if trade["sender_id"] == user_id else "Receiver"
                user_trades.append({
                    "trade_id": trade_id,
                    "role": role,
                    "status": trade["status"],
                    "other_user": trade["receiver_name"] if role == "Sender" else trade["sender_name"]
                })

        if not user_trades:
            return await message.reply_text("📭 You have no pending trades!")

        text = "📋 **Your Pending Trades**\n\n"
        for i, t in enumerate(user_trades, 1):
            text += f"{i}. With **{t['other_user']}** - {t['status']}\n"

        await message.reply_text(text)

    @app.on_message(filters.command(["canceltrade", "cancel"]))
    async def cancel_trade_cmd(client: Client, message: Message):
        """Cancel all active trades"""
        debug_log(f"canceltrade command from {message.from_user.id}")
        
        user_id = message.from_user.id
        cancelled = 0

        for trade_id in list(active_trades.keys()):
            trade = active_trades[trade_id]
            if trade["sender_id"] == user_id or trade["receiver_id"] == user_id:
                del active_trades[trade_id]
                cancelled += 1

        if cancelled:
            await message.reply_text(f"✅ Cancelled {cancelled} trade(s)!")
        else:
            await message.reply_text("📭 You have no active trades to cancel.")

    # Debug command to check trade state
    @app.on_message(filters.command(["debugtrade"]))
    async def debug_trade_cmd(client: Client, message: Message):
        """Debug command to check trade system state"""
        if not DEBUG_MODE:
            return

        text = f"🔧 **Trade System Debug**\n\n"
        text += f"Active trades: {len(active_trades)}\n"
        text += f"Cooldowns: {len(trade_cooldowns)}\n\n"

        for tid, trade in active_trades.items():
            text += f"**Trade:** `{tid[:20]}...`\n"
            text += f"  Status: {trade['status']}\n"
            text += f"  Sender: {trade['sender_name']}\n"
            text += f"  Receiver: {trade['receiver_name']}\n\n"

        await message.reply_text(text or "No data")

    debug_log("Trade module setup complete!")
