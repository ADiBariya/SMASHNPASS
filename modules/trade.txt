# modules/trade.py - Trade System (WORKS WITH YOUR DATABASE)

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

__MODULE__ = "Trade"
__HELP__ = """
🔄 **Trade Commands**
/trade @user - Start a trade
/mytrades - View pending trades
/canceltrade - Cancel your trade
"""

# Storage
active_trades = {}
trade_cooldowns = {}

# Debug
DEBUG = True
def debug(msg):
    if DEBUG:
        print(f"🔄 [TRADE] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def get_rarity_emoji(rarity: str) -> str:
    return {
        "common": "⚪",
        "rare": "🔵", 
        "epic": "🟣",
        "legendary": "🟡"
    }.get(str(rarity).lower(), "⚪")


def get_waifu_id(waifu: dict) -> int:
    """Get waifu ID as integer"""
    wid = waifu.get("waifu_id") or waifu.get("id") or waifu.get("_id") or 0
    try:
        return int(wid)
    except:
        return 0


def get_waifu_name(waifu: dict) -> str:
    return waifu.get("waifu_name") or waifu.get("name") or "Unknown"


def get_waifu_anime(waifu: dict) -> str:
    return waifu.get("waifu_anime") or waifu.get("anime") or "Unknown"


def get_waifu_rarity(waifu: dict) -> str:
    return str(waifu.get("waifu_rarity") or waifu.get("rarity") or "common").lower()


def get_waifu_power(waifu: dict) -> int:
    power = waifu.get("waifu_power") or waifu.get("power") or 0
    try:
        return int(power)
    except:
        return 0


def get_waifu_image(waifu: dict) -> str:
    return waifu.get("waifu_image") or waifu.get("image") or ""


def format_waifu(waifu: dict) -> str:
    """Format waifu for display"""
    if not waifu:
        return "❓ Unknown"
    
    emoji = get_rarity_emoji(get_waifu_rarity(waifu))
    name = get_waifu_name(waifu)
    anime = get_waifu_anime(waifu)
    power = get_waifu_power(waifu)
    wid = get_waifu_id(waifu)
    
    return f"{emoji} **{name}**\n📺 {anime}\n⚔️ Power: {power}\n🆔 ID: `{wid}`"


# ═══════════════════════════════════════════════════════════════════
#  Safe Message Helpers
# ═══════════════════════════════════════════════════════════════════

async def safe_edit(client, chat_id, msg_id, text, buttons=None):
    """Safely edit message"""
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=buttons
        )
        return True
    except:
        return False


async def safe_send(client, chat_id, text, buttons=None):
    """Safely send message"""
    try:
        return await client.send_message(chat_id=chat_id, text=text, reply_markup=buttons)
    except:
        return None


# ═══════════════════════════════════════════════════════════════════
#  /trade Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["trade", "tr"], config.COMMAND_PREFIX))
async def trade_command(client: Client, message: Message):
    """Start a trade"""
    user = message.from_user
    debug(f"Trade from {user.first_name} ({user.id})")
    
    # Cooldown check
    if user.id in trade_cooldowns:
        remaining = (trade_cooldowns[user.id] - datetime.now()).total_seconds()
        if remaining > 0:
            await message.reply_text(f"⏳ Wait {int(remaining)}s!")
            return
    
    # Get target
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) >= 2:
        try:
            target = await client.get_users(message.command[1])
        except:
            await message.reply_text("❌ User not found!")
            return
    else:
        await message.reply_text(
            "❌ **How to trade:**\n"
            "• Reply to user: `/trade`\n"
            "• Or: `/trade @username`"
        )
        return
    
    # Validate
    if not target:
        await message.reply_text("❌ User not found!")
        return
    if target.id == user.id:
        await message.reply_text("❌ Can't trade with yourself!")
        return
    if target.is_bot:
        await message.reply_text("❌ Can't trade with bots!")
        return
    
    # Check existing trade
    for t in active_trades.values():
        if t["sender_id"] == user.id:
            await message.reply_text("❌ You have an active trade!\nUse /canceltrade first.")
            return
    
    # Get collection using YOUR database method
    collection = db.get_full_collection(user.id)
    debug(f"Collection: {len(collection) if collection else 0} waifus")
    
    if not collection:
        await message.reply_text("❌ You have no waifus!\nPlay /smash first!")
        return
    
    # Create trade
    trade_id = f"{user.id % 100000}{int(datetime.now().timestamp()) % 100000}"
    debug(f"Trade ID: {trade_id}")
    
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
    
    # Build buttons - show first 10 unique waifus
    seen_ids = set()
    unique_waifus = []
    for w in collection:
        wid = get_waifu_id(w)
        if wid not in seen_ids:
            seen_ids.add(wid)
            unique_waifus.append(w)
        if len(unique_waifus) >= 10:
            break
    
    buttons = []
    row = []
    for i, w in enumerate(unique_waifus):
        name = get_waifu_name(w)[:12]
        row.append(InlineKeyboardButton(name, callback_data=f"tw_{trade_id}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")])
    
    # Store unique waifus for selection
    active_trades[trade_id]["sender_waifus"] = unique_waifus
    
    text = f"""
💘 **New Trade**

**From:** {user.mention}
**To:** {target.mention}

📦 Select a waifu to offer:
"""
    
    try:
        sent = await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        active_trades[trade_id]["msg_id"] = sent.id
    except Exception as e:
        del active_trades[trade_id]
        await message.reply_text(f"❌ Error: {e}")
        return
    
    trade_cooldowns[user.id] = datetime.now() + timedelta(seconds=30)


# ═══════════════════════════════════════════════════════════════════
#  Sender Selects Waifu
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tw_(\d+)_(\d+)$"))
async def sender_select_cb(client: Client, callback: CallbackQuery):
    """Sender picks waifu"""
    user = callback.from_user
    parts = callback.data.split("_")
    trade_id = parts[1]
    waifu_idx = int(parts[2])
    
    debug(f"Sender select: trade={trade_id}, idx={waifu_idx}")
    
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
    
    # Get from stored waifus
    sender_waifus = trade.get("sender_waifus", [])
    if waifu_idx >= len(sender_waifus):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = sender_waifus[waifu_idx]
    trade["sender_waifu"] = selected
    trade["status"] = "waiting"
    
    debug(f"Sender selected: {get_waifu_name(selected)} (ID: {get_waifu_id(selected)})")
    
    waifu_text = format_waifu(selected)
    
    # Update sender message
    try:
        await callback.message.edit_text(
            f"💘 **Trade in Progress**\n\n"
            f"**You offer:**\n{waifu_text}\n\n"
            f"⏳ Waiting for **{trade['receiver_name']}**...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")]
            ])
        )
    except:
        pass
    
    # Get receiver collection
    recv_collection = db.get_full_collection(trade["receiver_id"])
    if not recv_collection:
        await callback.message.edit_text(f"❌ {trade['receiver_name']} has no waifus!")
        del active_trades[trade_id]
        return
    
    # Get unique waifus for receiver
    seen_ids = set()
    unique_recv = []
    for w in recv_collection:
        wid = get_waifu_id(w)
        if wid not in seen_ids:
            seen_ids.add(wid)
            unique_recv.append(w)
        if len(unique_recv) >= 10:
            break
    
    trade["receiver_waifus"] = unique_recv
    
    # Build receiver buttons
    recv_buttons = []
    row = []
    for i, w in enumerate(unique_recv):
        name = get_waifu_name(w)[:12]
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

**They offer:**
{waifu_text}

📦 Select your waifu:
"""
    
    # Send to receiver
    recv_msg = await safe_send(client, trade["receiver_id"], recv_text, InlineKeyboardMarkup(recv_buttons))
    if recv_msg:
        trade["recv_chat_id"] = trade["receiver_id"]
        trade["recv_msg_id"] = recv_msg.id
        debug("Sent to receiver DM")
    else:
        recv_msg = await safe_send(client, trade["chat_id"], recv_text, InlineKeyboardMarkup(recv_buttons))
        if recv_msg:
            trade["recv_chat_id"] = trade["chat_id"]
            trade["recv_msg_id"] = recv_msg.id
            debug("Sent to group")
    
    await callback.answer("✅ Waifu selected!")


# ═══════════════════════════════════════════════════════════════════
#  Receiver Selects Waifu
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tr_(\d+)_(\d+)$"))
async def receiver_select_cb(client: Client, callback: CallbackQuery):
    """Receiver picks waifu"""
    user = callback.from_user
    parts = callback.data.split("_")
    trade_id = parts[1]
    waifu_idx = int(parts[2])
    
    debug(f"Receiver select: trade={trade_id}, idx={waifu_idx}")
    
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
    
    receiver_waifus = trade.get("receiver_waifus", [])
    if waifu_idx >= len(receiver_waifus):
        await callback.answer("❌ Waifu not found!", show_alert=True)
        return
    
    selected = receiver_waifus[waifu_idx]
    trade["receiver_waifu"] = selected
    trade["status"] = "confirm"
    
    debug(f"Receiver selected: {get_waifu_name(selected)} (ID: {get_waifu_id(selected)})")
    
    sender_text = format_waifu(trade["sender_waifu"])
    recv_text = format_waifu(selected)
    
    confirm_text = f"""
💘 **Confirm Trade**

**{trade['sender_name']}** offers:
{sender_text}

**{trade['receiver_name']}** offers:
{recv_text}

⚠️ Both click ✅ to complete!
"""
    
    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
        ]
    ])
    
    # Update all messages
    try:
        await callback.message.edit_text(confirm_text, reply_markup=confirm_buttons)
    except:
        pass
    
    await safe_edit(client, trade["chat_id"], trade["msg_id"], confirm_text, confirm_buttons)
    await safe_send(client, trade["sender_id"], confirm_text, confirm_buttons)
    
    await callback.answer("✅ Now both confirm!")


# ═══════════════════════════════════════════════════════════════════
#  Confirm Trade - USES YOUR DATABASE METHODS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^ty_(\d+)$"))
async def confirm_trade_cb(client: Client, callback: CallbackQuery):
    """Confirm trade"""
    user = callback.from_user
    trade_id = callback.data.split("_")[1]
    
    debug(f"Confirm: trade={trade_id}, user={user.id}")
    
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
        debug("Sender confirmed")
    else:
        if trade["receiver_ok"]:
            await callback.answer("Already confirmed!")
            return
        trade["receiver_ok"] = True
        debug("Receiver confirmed")
    
    await callback.answer("✅ Confirmed!")
    
    # Both confirmed?
    if trade["sender_ok"] and trade["receiver_ok"]:
        debug("=== EXECUTING TRADE ===")
        
        try:
            sender_id = trade["sender_id"]
            receiver_id = trade["receiver_id"]
            sender_waifu = trade["sender_waifu"]
            receiver_waifu = trade["receiver_waifu"]
            
            sender_wid = get_waifu_id(sender_waifu)
            receiver_wid = get_waifu_id(receiver_waifu)
            
            debug(f"Sender: {sender_id}, waifu ID: {sender_wid}")
            debug(f"Receiver: {receiver_id}, waifu ID: {receiver_wid}")
            
            # === STEP 1: Remove from original owners ===
            debug(f"Removing waifu {sender_wid} from sender {sender_id}")
            remove1 = db.remove_from_collection(sender_id, sender_wid)
            debug(f"Remove result 1: {remove1}")
            
            debug(f"Removing waifu {receiver_wid} from receiver {receiver_id}")
            remove2 = db.remove_from_collection(receiver_id, receiver_wid)
            debug(f"Remove result 2: {remove2}")
            
            # === STEP 2: Add to new owners (YOUR FORMAT) ===
            # Waifu for sender (receiver's waifu)
            waifu_for_sender = {
                "id": receiver_wid,
                "waifu_id": receiver_wid,
                "name": get_waifu_name(receiver_waifu),
                "waifu_name": get_waifu_name(receiver_waifu),
                "anime": get_waifu_anime(receiver_waifu),
                "waifu_anime": get_waifu_anime(receiver_waifu),
                "rarity": get_waifu_rarity(receiver_waifu),
                "waifu_rarity": get_waifu_rarity(receiver_waifu),
                "power": get_waifu_power(receiver_waifu),
                "waifu_power": get_waifu_power(receiver_waifu),
                "image": get_waifu_image(receiver_waifu),
                "waifu_image": get_waifu_image(receiver_waifu),
                "obtained_method": "trade"
            }
            
            # Waifu for receiver (sender's waifu)
            waifu_for_receiver = {
                "id": sender_wid,
                "waifu_id": sender_wid,
                "name": get_waifu_name(sender_waifu),
                "waifu_name": get_waifu_name(sender_waifu),
                "anime": get_waifu_anime(sender_waifu),
                "waifu_anime": get_waifu_anime(sender_waifu),
                "rarity": get_waifu_rarity(sender_waifu),
                "waifu_rarity": get_waifu_rarity(sender_waifu),
                "power": get_waifu_power(sender_waifu),
                "waifu_power": get_waifu_power(sender_waifu),
                "image": get_waifu_image(sender_waifu),
                "waifu_image": get_waifu_image(sender_waifu),
                "obtained_method": "trade"
            }
            
            debug(f"Adding to sender: {waifu_for_sender}")
            add1 = db.add_to_collection(sender_id, waifu_for_sender)
            debug(f"Add result 1: {add1}")
            
            debug(f"Adding to receiver: {waifu_for_receiver}")
            add2 = db.add_to_collection(receiver_id, waifu_for_receiver)
            debug(f"Add result 2: {add2}")
            
            debug("=== DATABASE UPDATED ===")
            
            # Success message
            success_text = f"""
🎉 **Trade Complete!** 🎉

**{trade['sender_name']}** received:
{format_waifu(waifu_for_sender)}

**{trade['receiver_name']}** received:
{format_waifu(waifu_for_receiver)}

💖 Enjoy your new waifus!
"""
            
            # Update ALL messages
            try:
                await callback.message.edit_text(success_text)
            except:
                pass
            
            await safe_edit(client, trade["chat_id"], trade["msg_id"], success_text)
            
            if trade.get("recv_msg_id"):
                await safe_edit(client, trade["recv_chat_id"], trade["recv_msg_id"], success_text)
            
            await safe_send(client, trade["sender_id"], success_text)
            await safe_send(client, trade["receiver_id"], success_text)
            
            # Group notification
            await safe_send(
                client, trade["chat_id"],
                f"✅ **Trade Done!** {trade['sender_name']} ↔️ {trade['receiver_name']} 💖"
            )
            
            debug("Trade completed successfully!")
            
        except Exception as e:
            debug(f"TRADE ERROR: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(f"❌ Trade failed: {e}")
        
        # Cleanup
        if trade_id in active_trades:
            del active_trades[trade_id]
    
    else:
        # Show status
        s = "✅" if trade["sender_ok"] else "⏳"
        r = "✅" if trade["receiver_ok"] else "⏳"
        
        status_text = f"""
💘 **Trade Confirmation**

**{trade['sender_name']}:** {s}
**{trade['receiver_name']}:** {r}

⏳ Waiting for both...
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"ty_{trade_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"tc_{trade_id}")
            ]
        ])
        
        try:
            await callback.message.edit_text(status_text, reply_markup=buttons)
        except:
            pass
        
        await safe_edit(client, trade["chat_id"], trade["msg_id"], status_text, buttons)


# ═══════════════════════════════════════════════════════════════════
#  Cancel Trade
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^tc_(\d+)$"))
async def cancel_trade_cb(client: Client, callback: CallbackQuery):
    """Cancel trade"""
    user = callback.from_user
    trade_id = callback.data.split("_")[1]
    
    if trade_id not in active_trades:
        await callback.answer("❌ Already cancelled!", show_alert=True)
        return
    
    trade = active_trades[trade_id]
    
    if user.id not in [trade["sender_id"], trade["receiver_id"]]:
        await callback.answer("❌ Not your trade!", show_alert=True)
        return
    
    cancel_text = f"❌ **Trade Cancelled**\n\nCancelled by **{user.first_name}**"
    
    try:
        await callback.message.edit_text(cancel_text)
    except:
        pass
    
    await safe_edit(client, trade["chat_id"], trade["msg_id"], cancel_text)
    
    if trade.get("recv_msg_id"):
        await safe_edit(client, trade["recv_chat_id"], trade["recv_msg_id"], cancel_text)
    
    other_id = trade["receiver_id"] if user.id == trade["sender_id"] else trade["sender_id"]
    await safe_send(client, other_id, cancel_text)
    
    del active_trades[trade_id]
    debug(f"Trade {trade_id} cancelled")
    
    await callback.answer("Cancelled!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  Commands
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["mytrades", "trades"], config.COMMAND_PREFIX))
async def mytrades_cmd(client: Client, message: Message):
    user = message.from_user
    
    my = []
    for t in active_trades.values():
        if t["sender_id"] == user.id:
            my.append(f"📤 To **{t['receiver_name']}** ({t['status']})")
        elif t["receiver_id"] == user.id:
            my.append(f"📥 From **{t['sender_name']}** ({t['status']})")
    
    if not my:
        await message.reply_text("📭 No pending trades!")
    else:
        await message.reply_text("📋 **Your Trades**\n\n" + "\n".join(my))


@Client.on_message(filters.command(["canceltrade", "ctrade"], config.COMMAND_PREFIX))
async def canceltrade_cmd(client: Client, message: Message):
    user = message.from_user
    
    count = 0
    for tid in list(active_trades.keys()):
        t = active_trades[tid]
        if t["sender_id"] == user.id or t["receiver_id"] == user.id:
            del active_trades[tid]
            count += 1
    
    if count:
        await message.reply_text(f"✅ Cancelled {count} trade(s)!")
    else:
        await message.reply_text("📭 No trades to cancel.")


@Client.on_message(filters.command("debugtrade", config.COMMAND_PREFIX))
async def debugtrade_cmd(client: Client, message: Message):
    if not DEBUG:
        return
    
    text = f"🔧 **Trade Debug**\n\nActive: {len(active_trades)}\n\n"
    
    for tid, t in active_trades.items():
        text += f"`{tid}`\n"
        text += f"├ {t['sender_name']} → {t['receiver_name']}\n"
        text += f"├ Status: {t['status']}\n"
        text += f"└ OK: S={t['sender_ok']} R={t['receiver_ok']}\n\n"
    
    await message.reply_text(text or "No trades")
