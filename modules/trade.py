# modules/trade.py - Trade System (start.py style)

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from database import db
import config
from datetime import datetime, timedelta

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
    emoji = get_rarity_emoji(rarity)
    
    return f"{emoji} **{name}**\n📺 {anime}\n⚔️ Power: {power}"


def get_waifu_id(waifu: dict) -> str:
    """Get waifu ID safely"""
    return str(waifu.get("waifu_id") or waifu.get("id") or waifu.get("_id", "0"))


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
    
    # Method 1: Reply
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        debug(f"Target from reply: {target.id}")
    
    # Method 2: Username/ID
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
    
    # Create trade ID (short)
    trade_id = f"{user.id % 10000}{int(datetime.now().timestamp()) % 100000}"
    debug(f"Created trade_id: {trade_id}")
    
    # Store trade
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
        "msg_id": None
    }
    
    # Build waifu buttons (max 10)
    buttons = []
    row = []
    
    for i, waifu in enumerate(collection[:10]):
        wid = get_waifu_id(waifu)
        name = (waifu.get("waifu_name") or waifu.get("name", "?"))[:12]
        
        # Short callback: tw_{trade_id}_{waifu_index}
        row.append(InlineKeyboardButton(name, callback_data=f"tw_{trade_id}_{i}"))
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")])
    
    text = f"""
💘 **New Trade**

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
    
    # Set cooldown
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
    
    # Check trade exists
    if trade_id not in active_trades:
        await callback.answer("❌ Trade expired!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    # Check user is sender
    if trade["sender_id"] != user.id:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    # Check status
    if trade["status"] != "picking":
        await callback.answer("❌ Already selected!", show_alert=True)
        return
    
    # Get collection
    try:
        collection = db.get_user_collection(user.id)
    except:
        await callback.answer("❌ DB Error!", show_alert=True)
        return
    
    if not collection or waifu_idx >= len(collection):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    # Get selected waifu
    selected = collection[waifu_idx]
    trade["sender_waifu"] = selected
    trade["status"] = "waiting"
    
    debug(f"Sender selected: {selected.get('waifu_name') or selected.get('name')}")
    
    # Update message
    waifu_text = format_waifu(selected)
    
    await callback.message.edit_text(
        f"💘 **Trade in Progress**\n\n"
        f"**You offered:**\n{waifu_text}\n\n"
        f"⏳ Waiting for {trade['receiver_name']}...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")]
        ])
    )
    
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
    
    # Notify receiver
    try:
        await client.send_message(
            trade["receiver_id"],
            f"💘 **Trade Request!**\n\n"
            f"**From:** {trade['sender_name']}\n\n"
            f"**They offer:**\n{waifu_text}\n\n"
            f"📦 Select your waifu to trade:",
            reply_markup=InlineKeyboardMarkup(recv_buttons)
        )
        debug(f"Notified receiver: {trade['receiver_id']}")
    except Exception as e:
        debug(f"Can't DM receiver: {e}")
        # Try in group
        try:
            await client.send_message(
                trade["chat_id"],
                f"💘 **{trade['receiver_name']}!**\n\n"
                f"{trade['sender_name']} wants to trade!\n\n"
                f"**Offering:**\n{waifu_text}\n\n"
                f"📦 Select your waifu:",
                reply_markup=InlineKeyboardMarkup(recv_buttons)
            )
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
    
    # Get collection
    try:
        collection = db.get_user_collection(user.id)
    except:
        await callback.answer("❌ DB Error!", show_alert=True)
        return
    
    if not collection or waifu_idx >= len(collection):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    # Get selected
    selected = collection[waifu_idx]
    trade["receiver_waifu"] = selected
    trade["status"] = "confirm"
    
    debug(f"Receiver selected: {selected.get('waifu_name') or selected.get('name')}")
    
    # Format both waifus
    sender_text = format_waifu(trade["sender_waifu"])
    recv_text = format_waifu(selected)
    
    confirm_text = f"""
💘 **Confirm Trade**

**{trade['sender_name']}** offers:
{sender_text}

**{trade['receiver_name']}** offers:
{recv_text}

Both must click ✅ to complete!
"""
    
    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
        ]
    ])
    
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
        debug(f"Can't notify sender: {e}")
    
    await callback.answer("✅ Now both confirm!")


# ═══════════════════════════════════════════════════════════════════
#  Confirm Trade Callback
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
            # Get waifu IDs
            sender_waifu = trade["sender_waifu"]
            recv_waifu = trade["receiver_waifu"]
            
            sender_wid = get_waifu_id(sender_waifu)
            recv_wid = get_waifu_id(recv_waifu)
            
            debug(f"Swapping: {sender_wid} <-> {recv_wid}")
            
            # Remove from original owners
            db.remove_from_collection(trade["sender_id"], sender_wid)
            db.remove_from_collection(trade["receiver_id"], recv_wid)
            
            # Add to new owners
            db.add_to_collection(trade["sender_id"], recv_waifu)
            db.add_to_collection(trade["receiver_id"], sender_waifu)
            
            # Success message
            success_text = f"""
🎉 **Trade Complete!** 🎉

**{trade['sender_name']}** received:
{format_waifu(recv_waifu)}

**{trade['receiver_name']}** received:
{format_waifu(sender_waifu)}

Enjoy your new waifus! 💖
"""
            
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
            
            debug("Trade completed successfully!")
            
        except Exception as e:
            debug(f"Trade execution error: {e}")
            await callback.message.edit_text(f"❌ Trade failed: {e}")
        
        # Cleanup
        del active_trades[trade_id]
    
    else:
        # Update status
        s_status = "✅" if trade["sender_ok"] else "⏳"
        r_status = "✅" if trade["receiver_ok"] else "⏳"
        
        status_text = f"""
💘 **Trade Confirmation**

**{trade['sender_name']}:** {s_status}
**{trade['receiver_name']}:** {r_status}

Waiting for both to confirm...
"""
        
        try:
            await callback.message.edit_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
                    ]
                ])
            )
        except:
            pass


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
    
    # Cancel
    try:
        await callback.message.edit_text(
            f"❌ **Trade Cancelled**\n\n"
            f"Cancelled by {user.first_name}"
        )
    except:
        pass
    
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
        if t["sender_id"] == user.id:
            my_trades.append(f"📤 To **{t['receiver_name']}** - {t['status']}")
        elif t["receiver_id"] == user.id:
            my_trades.append(f"📥 From **{t['sender_name']}** - {t['status']}")
    
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
#  Debug Command (optional)
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
        text += f"• `{tid}`: {t['sender_name']} → {t['receiver_name']} ({t['status']})\n"
    
    await message.reply_text(text or "No data")
