# modules/trade.py - Trade System (FIXED)

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.errors import MessageNotModified
from database import db
import config
from datetime import datetime, timedelta
import traceback

# Module info
__MODULE__ = "Trade"
__HELP__ = """
🔄 **Trade Commands**
/trade @user - Start a trade
/mytrades - View pending trades
/canceltrade - Cancel your trade
"""

# Active trades storage
active_trades = {}

# Trade cooldowns
trade_cooldowns = {}

# Debug mode
DEBUG = True

def debug(msg):
    if DEBUG:
        print(f"🔄 [TRADE] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity"""
    return {
        "common": "⚪",
        "rare": "🔵", 
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(rarity).lower(), "⚪")


def format_waifu(waifu: dict) -> str:
    """Format waifu info for display"""
    if not waifu:
        return "❓ Unknown"
    
    name = waifu.get("waifu_name") or waifu.get("name", "Unknown")
    rarity = waifu.get("waifu_rarity") or waifu.get("rarity", "common")
    power = waifu.get("waifu_power") or waifu.get("power", 0)
    anime = waifu.get("waifu_anime") or waifu.get("anime", "Unknown")
    wid = get_waifu_id(waifu)
    emoji = get_rarity_emoji(rarity)
    
    return f"{emoji} **{name}**\n📺 {anime}\n⚔️ Power: {power}\n🆔 ID: `{wid}`"


def get_waifu_id(waifu: dict):
    """Get waifu ID safely - keep original type"""
    wid = waifu.get("waifu_id") or waifu.get("id") or waifu.get("_id")
    return wid


def get_waifu_id_str(waifu: dict) -> str:
    """Get waifu ID as string for comparison"""
    wid = get_waifu_id(waifu)
    return str(wid) if wid else "0"


def prepare_waifu_for_new_owner(waifu: dict, new_owner_id: int) -> dict:
    """Prepare waifu data for adding to new owner's collection"""
    # Create a clean copy
    new_waifu = {
        "waifu_id": waifu.get("waifu_id") or waifu.get("id") or waifu.get("_id"),
        "waifu_name": waifu.get("waifu_name") or waifu.get("name", "Unknown"),
        "waifu_anime": waifu.get("waifu_anime") or waifu.get("anime", "Unknown"),
        "waifu_rarity": waifu.get("waifu_rarity") or waifu.get("rarity", "common"),
        "waifu_power": waifu.get("waifu_power") or waifu.get("power", 0),
        "waifu_image": waifu.get("waifu_image") or waifu.get("image", ""),
        "obtained_at": datetime.now().isoformat(),
        "obtained_via": "trade"
    }
    
    # Also add alternative field names for compatibility
    new_waifu["id"] = new_waifu["waifu_id"]
    new_waifu["name"] = new_waifu["waifu_name"]
    new_waifu["anime"] = new_waifu["waifu_anime"]
    new_waifu["rarity"] = new_waifu["waifu_rarity"]
    new_waifu["power"] = new_waifu["waifu_power"]
    new_waifu["image"] = new_waifu["waifu_image"]
    
    debug(f"Prepared waifu for transfer: {new_waifu['waifu_name']} (ID: {new_waifu['waifu_id']})")
    return new_waifu


async def safe_edit_message(client, chat_id, message_id, text, reply_markup=None):
    """Safely edit a message, ignoring errors"""
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
        return True
    except MessageNotModified:
        return True
    except Exception as e:
        debug(f"Error editing message {message_id} in {chat_id}: {e}")
        return False


async def safe_send_message(client, chat_id, text, reply_markup=None):
    """Safely send a message, ignoring errors"""
    try:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        debug(f"Error sending message to {chat_id}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
#  /trade Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["trade", "tr"], config.COMMAND_PREFIX))
async def trade_command(client: Client, message: Message):
    """Start a trade with another user"""
    user = message.from_user
    debug(f"Trade command from {user.first_name} ({user.id})")
    
    # Check cooldown
    if user.id in trade_cooldowns:
        remaining = (trade_cooldowns[user.id] - datetime.now()).total_seconds()
        if remaining > 0:
            await message.reply_text(f"⏳ Wait {int(remaining)}s before trading again!")
            return
    
    # Get target user
    target = None
    
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        debug(f"Target from reply: {target.id}")
    elif len(message.command) >= 2:
        try:
            target = await client.get_users(message.command[1])
            debug(f"Target from arg: {target.id}")
        except Exception as e:
            debug(f"Error getting user: {e}")
            await message.reply_text("❌ User not found!")
            return
    else:
        await message.reply_text(
            "❌ **How to trade:**\n"
            "• Reply to user: `/trade`\n"
            "• Or use: `/trade @username`"
        )
        return
    
    # Validations
    if not target:
        await message.reply_text("❌ Could not find user!")
        return
    
    if target.id == user.id:
        await message.reply_text("❌ You can't trade with yourself!")
        return
    
    if target.is_bot:
        await message.reply_text("❌ Can't trade with bots!")
        return
    
    # Check for existing trade
    for tid, t in active_trades.items():
        if t["sender_id"] == user.id:
            await message.reply_text(
                "❌ You have an active trade!\n"
                "Use /canceltrade to cancel it first."
            )
            return
    
    # Get user's collection
    try:
        collection = db.get_user_collection(user.id)
        debug(f"User collection: {len(collection) if collection else 0} waifus")
    except Exception as e:
        debug(f"DB Error: {e}")
        await message.reply_text(f"❌ Database error: {e}")
        return
    
    if not collection or len(collection) == 0:
        await message.reply_text(
            "❌ You don't have any waifus!\n"
            "Play /smash to collect some first!"
        )
        return
    
    # Create unique trade ID
    trade_id = f"{user.id % 100000}{int(datetime.now().timestamp()) % 100000}"
    debug(f"Created trade_id: {trade_id}")
    
    # Store trade with all tracking info
    active_trades[trade_id] = {
        "sender_id": user.id,
        "sender_name": user.first_name,
        "receiver_id": target.id,
        "receiver_name": target.first_name,
        "sender_waifu": None,
        "receiver_waifu": None,
        "sender_ok": False,
        "receiver_ok": False,
        "status": "picking",
        "chat_id": message.chat.id,
        "msg_id": None,
        "recv_chat_id": None,
        "recv_msg_id": None
    }
    
    # Build waifu buttons (max 10)
    buttons = []
    row = []
    
    for i, waifu in enumerate(collection[:10]):
        name = (waifu.get("waifu_name") or waifu.get("name", "?"))[:12]
        row.append(InlineKeyboardButton(name, callback_data=f"tw_{trade_id}_{i}"))
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")])
    
    text = f"""
💘 **New Trade Request**

**From:** {user.mention}
**To:** {target.mention}

📦 Select a waifu to offer:
"""
    
    try:
        sent = await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        active_trades[trade_id]["msg_id"] = sent.id
        debug(f"Trade message sent: {sent.id}")
    except Exception as e:
        debug(f"Error sending: {e}")
        del active_trades[trade_id]
        await message.reply_text(f"❌ Error: {e}")
        return
    
    trade_cooldowns[user.id] = datetime.now() + timedelta(seconds=30)


# ═══════════════════════════════════════════════════════════════════
#  Sender Selects Waifu Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tw_(\d+)_(\d+)$"))
async def sender_select_callback(client: Client, callback: CallbackQuery):
    """Sender picks their waifu"""
    user = callback.from_user
    data = callback.data
    debug(f"Sender select: {data} from {user.id}")
    
    try:
        parts = data.split("_")
        trade_id = parts[1]
        waifu_idx = int(parts[2])
    except:
        await callback.answer("❌ Invalid!", show_alert=True)
        return
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if trade["sender_id"] != user.id:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    if trade["status"] != "picking":
        await callback.answer("❌ Already selected!", show_alert=True)
        return
    
    try:
        collection = db.get_user_collection(user.id)
    except:
        await callback.answer("❌ DB Error!", show_alert=True)
        return
    
    if not collection or waifu_idx >= len(collection):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = collection[waifu_idx]
    trade["sender_waifu"] = selected
    trade["status"] = "waiting"
    
    debug(f"Sender selected: {selected.get('waifu_name') or selected.get('name')}")
    
    waifu_text = format_waifu(selected)
    
    # Update sender's message
    try:
        await callback.message.edit_text(
            f"💘 **Trade in Progress**\n\n"
            f"**You offered:**\n{waifu_text}\n\n"
            f"⏳ Waiting for **{trade['receiver_name']}** to respond...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")]
            ])
        )
    except:
        pass
    
    # Get receiver's collection
    try:
        recv_collection = db.get_user_collection(trade["receiver_id"])
    except:
        await callback.message.edit_text("❌ Receiver has no collection!")
        del active_trades[trade_id]
        return
    
    if not recv_collection:
        await callback.message.edit_text(
            f"❌ {trade['receiver_name']} has no waifus to trade!"
        )
        del active_trades[trade_id]
        await callback.answer("Trade cancelled!")
        return
    
    # Build buttons for receiver
    recv_buttons = []
    row = []
    
    for i, waifu in enumerate(recv_collection[:10]):
        name = (waifu.get("waifu_name") or waifu.get("name", "?"))[:12]
        row.append(InlineKeyboardButton(name, callback_data=f"tr_{trade_id}_{i}"))
        
        if len(row) == 2:
            recv_buttons.append(row)
            row = []
    
    if row:
        recv_buttons.append(row)
    
    recv_buttons.append([InlineKeyboardButton("❌ Decline", callback_data=f"tc_{trade_id}")])
    
    recv_text = f"""
💘 **Trade Request!**

**From:** {trade['sender_name']}

**They're offering:**
{waifu_text}

📦 Select your waifu to trade:
"""
    
    # Notify receiver via DM
    try:
        recv_msg = await client.send_message(
            trade["receiver_id"],
            recv_text,
            reply_markup=InlineKeyboardMarkup(recv_buttons)
        )
        trade["recv_chat_id"] = trade["receiver_id"]
        trade["recv_msg_id"] = recv_msg.id
        debug(f"Notified receiver via DM: {trade['receiver_id']}")
    except Exception as e:
        debug(f"Can't DM receiver: {e}")
        # Try in group
        try:
            recv_msg = await client.send_message(
                trade["chat_id"],
                f"💘 **Hey {trade['receiver_name']}!**\n\n"
                f"{trade['sender_name']} wants to trade with you!\n\n"
                f"**Offering:**\n{waifu_text}\n\n"
                f"📦 Select your waifu:",
                reply_markup=InlineKeyboardMarkup(recv_buttons)
            )
            trade["recv_chat_id"] = trade["chat_id"]
            trade["recv_msg_id"] = recv_msg.id
            debug(f"Notified receiver in group")
        except Exception as e2:
            debug(f"Group notify failed: {e2}")
    
    await callback.answer("✅ Waifu selected!")


# ═══════════════════════════════════════════════════════════════════
#  Receiver Selects Waifu Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tr_(\d+)_(\d+)$"))
async def receiver_select_callback(client: Client, callback: CallbackQuery):
    """Receiver picks their waifu"""
    user = callback.from_user
    data = callback.data
    debug(f"Receiver select: {data} from {user.id}")
    
    try:
        parts = data.split("_")
        trade_id = parts[1]
        waifu_idx = int(parts[2])
    except:
        await callback.answer("❌ Invalid!", show_alert=True)
        return
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if trade["receiver_id"] != user.id:
        await callback.answer("❌ Not for you!", show_alert=True)
        return
    
    if trade["status"] != "waiting":
        await callback.answer("❌ Invalid state!", show_alert=True)
        return
    
    try:
        collection = db.get_user_collection(user.id)
    except:
        await callback.answer("❌ DB Error!", show_alert=True)
        return
    
    if not collection or waifu_idx >= len(collection):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = collection[waifu_idx]
    trade["receiver_waifu"] = selected
    trade["status"] = "confirm"
    
    debug(f"Receiver selected: {selected.get('waifu_name') or selected.get('name')}")
    
    sender_text = format_waifu(trade["sender_waifu"])
    recv_text = format_waifu(selected)
    
    confirm_text = f"""
💘 **Confirm Trade**

**{trade['sender_name']}** offers:
{sender_text}

**{trade['receiver_name']}** offers:
{recv_text}

⚠️ Both must click ✅ to complete!
"""
    
    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
        ]
    ])
    
    # Update receiver's message (current)
    try:
        await callback.message.edit_text(confirm_text, reply_markup=confirm_buttons)
    except:
        pass
    
    # Update sender's original message in group
    await safe_edit_message(client, trade["chat_id"], trade["msg_id"], confirm_text, confirm_buttons)
    
    # Also send to sender's DM
    await safe_send_message(client, trade["sender_id"], confirm_text, confirm_buttons)
    
    await callback.answer("✅ Now both confirm!")


# ═══════════════════════════════════════════════════════════════════
#  Confirm Trade Callback - THE MAIN FIX
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^ty_(\d+)$"))
async def confirm_trade_callback(client: Client, callback: CallbackQuery):
    """Confirm the trade"""
    user = callback.from_user
    data = callback.data
    debug(f"Confirm: {data} from {user.id}")
    
    try:
        trade_id = data.split("_")[1]
    except:
        await callback.answer("❌ Invalid!", show_alert=True)
        return
    
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if user.id not in [trade["sender_id"], trade["receiver_id"]]:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    if trade["status"] != "confirm":
        await callback.answer("❌ Not ready!", show_alert=True)
        return
    
    # Mark confirmed
    if user.id == trade["sender_id"]:
        if trade["sender_ok"]:
            await callback.answer("Already confirmed!")
            return
        trade["sender_ok"] = True
        debug(f"Sender confirmed")
    else:
        if trade["receiver_ok"]:
            await callback.answer("Already confirmed!")
            return
        trade["receiver_ok"] = True
        debug(f"Receiver confirmed")
    
    await callback.answer("✅ Confirmed!")
    
    # Check if both confirmed
    if trade["sender_ok"] and trade["receiver_ok"]:
        debug("Both confirmed! Executing trade...")
        
        try:
            sender_waifu = trade["sender_waifu"]
            recv_waifu = trade["receiver_waifu"]
            
            sender_id = trade["sender_id"]
            receiver_id = trade["receiver_id"]
            
            sender_wid = get_waifu_id(sender_waifu)
            recv_wid = get_waifu_id(recv_waifu)
            
            debug(f"Trade details:")
            debug(f"  Sender ID: {sender_id}")
            debug(f"  Receiver ID: {receiver_id}")
            debug(f"  Sender waifu ID: {sender_wid} (type: {type(sender_wid)})")
            debug(f"  Receiver waifu ID: {recv_wid} (type: {type(recv_wid)})")
            
            # Prepare waifus for new owners
            waifu_for_sender = prepare_waifu_for_new_owner(recv_waifu, sender_id)
            waifu_for_receiver = prepare_waifu_for_new_owner(sender_waifu, receiver_id)
            
            # STEP 1: Remove waifus from original owners
            debug(f"Removing waifu {sender_wid} from sender {sender_id}...")
            try:
                # Try multiple removal methods
                result1 = db.remove_from_collection(sender_id, sender_wid)
                debug(f"Remove from sender result: {result1}")
            except Exception as e:
                debug(f"Error removing from sender: {e}")
                # Try alternative method
                try:
                    db.users.update_one(
                        {"user_id": sender_id},
                        {"$pull": {"collection": {"$or": [
                            {"waifu_id": sender_wid},
                            {"id": sender_wid},
                            {"waifu_id": str(sender_wid)},
                            {"id": str(sender_wid)}
                        ]}}}
                    )
                except Exception as e2:
                    debug(f"Alternative remove from sender failed: {e2}")
            
            debug(f"Removing waifu {recv_wid} from receiver {receiver_id}...")
            try:
                result2 = db.remove_from_collection(receiver_id, recv_wid)
                debug(f"Remove from receiver result: {result2}")
            except Exception as e:
                debug(f"Error removing from receiver: {e}")
                try:
                    db.users.update_one(
                        {"user_id": receiver_id},
                        {"$pull": {"collection": {"$or": [
                            {"waifu_id": recv_wid},
                            {"id": recv_wid},
                            {"waifu_id": str(recv_wid)},
                            {"id": str(recv_wid)}
                        ]}}}
                    )
                except Exception as e2:
                    debug(f"Alternative remove from receiver failed: {e2}")
            
            # STEP 2: Add waifus to new owners
            debug(f"Adding waifu to sender {sender_id}...")
            try:
                result3 = db.add_to_collection(sender_id, waifu_for_sender)
                debug(f"Add to sender result: {result3}")
            except Exception as e:
                debug(f"Error adding to sender: {e}")
                # Try alternative method
                try:
                    db.users.update_one(
                        {"user_id": sender_id},
                        {"$push": {"collection": waifu_for_sender}},
                        upsert=True
                    )
                except Exception as e2:
                    debug(f"Alternative add to sender failed: {e2}")
            
            debug(f"Adding waifu to receiver {receiver_id}...")
            try:
                result4 = db.add_to_collection(receiver_id, waifu_for_receiver)
                debug(f"Add to receiver result: {result4}")
            except Exception as e:
                debug(f"Error adding to receiver: {e}")
                try:
                    db.users.update_one(
                        {"user_id": receiver_id},
                        {"$push": {"collection": waifu_for_receiver}},
                        upsert=True
                    )
                except Exception as e2:
                    debug(f"Alternative add to receiver failed: {e2}")
            
            # Success message
            success_text = f"""
🎉 **Trade Completed!** 🎉

**{trade['sender_name']}** received:
{format_waifu(waifu_for_sender)}

**{trade['receiver_name']}** received:
{format_waifu(waifu_for_receiver)}

💖 Enjoy your new waifus!
"""
            
            # Update ALL messages
            
            # 1. Current callback message
            try:
                await callback.message.edit_text(success_text)
            except:
                pass
            
            # 2. Original group message
            await safe_edit_message(client, trade["chat_id"], trade["msg_id"], success_text)
            
            # 3. Receiver's message (if different)
            if trade.get("recv_chat_id") and trade.get("recv_msg_id"):
                if not (trade["recv_chat_id"] == callback.message.chat.id and 
                        trade["recv_msg_id"] == callback.message.id):
                    await safe_edit_message(client, trade["recv_chat_id"], trade["recv_msg_id"], success_text)
            
            # 4. Send DM notifications
            await safe_send_message(client, trade["sender_id"], success_text)
            await safe_send_message(client, trade["receiver_id"], success_text)
            
            # 5. Send group notification
            await safe_send_message(
                client, 
                trade["chat_id"],
                f"✅ **Trade Complete!**\n\n"
                f"**{trade['sender_name']}** ↔️ **{trade['receiver_name']}**\n\n"
                f"Both have received their new waifus! 💖"
            )
            
            debug("Trade completed successfully!")
            
        except Exception as e:
            debug(f"Trade execution error: {e}")
            traceback.print_exc()
            
            error_text = f"❌ **Trade Failed!**\n\nError: {str(e)}"
            try:
                await callback.message.edit_text(error_text)
            except:
                pass
        
        # Cleanup
        if trade_id in active_trades:
            del active_trades[trade_id]
    
    else:
        # Update status
        s_status = "✅" if trade["sender_ok"] else "⏳"
        r_status = "✅" if trade["receiver_ok"] else "⏳"
        
        sender_text = format_waifu(trade["sender_waifu"])
        recv_text = format_waifu(trade["receiver_waifu"])
        
        status_text = f"""
💘 **Trade Confirmation**

**{trade['sender_name']}** {s_status}
{sender_text}

**{trade['receiver_name']}** {r_status}
{recv_text}

⏳ Waiting for both to confirm...
"""
        
        confirm_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
            ]
        ])
        
        # Update current message
        try:
            await callback.message.edit_text(status_text, reply_markup=confirm_buttons)
        except:
            pass
        
        # Update group message
        await safe_edit_message(client, trade["chat_id"], trade["msg_id"], status_text, confirm_buttons)


# ═══════════════════════════════════════════════════════════════════
#  Cancel Trade Callback
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tc_(\d+)$"))
async def cancel_trade_callback(client: Client, callback: CallbackQuery):
    """Cancel the trade"""
    user = callback.from_user
    data = callback.data
    debug(f"Cancel: {data} from {user.id}")
    
    try:
        trade_id = data.split("_")[1]
    except:
        await callback.answer("❌ Invalid!", show_alert=True)
        return
    
    if trade_id not in active_trades:
        await callback.answer("❌ Already cancelled!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if user.id not in [trade["sender_id"], trade["receiver_id"]]:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    cancel_text = f"""
❌ **Trade Cancelled**

Cancelled by **{user.first_name}**

No waifus were exchanged.
"""
    
    # Update all messages
    try:
        await callback.message.edit_text(cancel_text)
    except:
        pass
    
    await safe_edit_message(client, trade["chat_id"], trade["msg_id"], cancel_text)
    
    if trade.get("recv_chat_id") and trade.get("recv_msg_id"):
        await safe_edit_message(client, trade["recv_chat_id"], trade["recv_msg_id"], cancel_text)
    
    # Notify other party
    other_id = trade["receiver_id"] if user.id == trade["sender_id"] else trade["sender_id"]
    await safe_send_message(client, other_id, cancel_text)
    
    del active_trades[trade_id]
    debug(f"Trade {trade_id} cancelled")
    
    await callback.answer("Trade cancelled!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  /mytrades Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["mytrades", "trades"], config.COMMAND_PREFIX))
async def mytrades_command(client: Client, message: Message):
    """View your pending trades"""
    user = message.from_user
    debug(f"mytrades from {user.id}")
    
    my_trades = []
    
    for tid, t in active_trades.items():
        status_emoji = {"picking": "📝", "waiting": "⏳", "confirm": "✅"}.get(t["status"], "❓")
        
        if t["sender_id"] == user.id:
            my_trades.append(f"{status_emoji} To **{t['receiver_name']}** ({t['status']})")
        elif t["receiver_id"] == user.id:
            my_trades.append(f"{status_emoji} From **{t['sender_name']}** ({t['status']})")
    
    if not my_trades:
        await message.reply_text("📭 You have no pending trades!")
        return
    
    text = "📋 **Your Trades**\n\n" + "\n".join(my_trades)
    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  /canceltrade Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["canceltrade", "ctrade"], config.COMMAND_PREFIX))
async def canceltrade_command(client: Client, message: Message):
    """Cancel all your trades"""
    user = message.from_user
    debug(f"canceltrade from {user.id}")
    
    cancelled = 0
    
    for tid in list(active_trades.keys()):
        t = active_trades[tid]
        if t["sender_id"] == user.id or t["receiver_id"] == user.id:
            del active_trades[tid]
            cancelled += 1
    
    if cancelled:
        await message.reply_text(f"✅ Cancelled {cancelled} trade(s)!")
    else:
        await message.reply_text("📭 No active trades to cancel.")


# ═══════════════════════════════════════════════════════════════════
#  Debug Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("debugtrade", config.COMMAND_PREFIX))
async def debug_trade_command(client: Client, message: Message):
    """Debug trade system"""
    if not DEBUG:
        return
    
    text = f"🔧 **Trade Debug**\n\n"
    text += f"Active: {len(active_trades)}\n"
    text += f"Cooldowns: {len(trade_cooldowns)}\n\n"
    
    for tid, t in active_trades.items():
        text += f"**{tid}**\n"
        text += f"├ Status: {t['status']}\n"
        text += f"├ {t['sender_name']} → {t['receiver_name']}\n"
        text += f"├ Sender OK: {t['sender_ok']}\n"
        text += f"└ Receiver OK: {t['receiver_ok']}\n\n"
    
    await message.reply_text(text or "No active trades")
