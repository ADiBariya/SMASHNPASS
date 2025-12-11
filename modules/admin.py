# plugins/admin.py - Enhanced Admin Commands

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import COMMAND_PREFIX, OWNER_ID, SUDO_USERS
from helpers.utils import load_waifus, save_waifus
from datetime import datetime, timedelta
import json
import os
import asyncio

__MODULE__ = "Admin"
__HELP__ = """
👑 **Admin Commands** (Owner Only)

**💰 Economy:**
`.addcoins @user <amount>` - Add coins
`.removecoins @user <amount>` - Remove coins
`.setcoins @user <amount>` - Set exact coins

**🎴 Waifu Management:**
`.addwaifu` - Add new waifu (reply to JSON)
`.delwaifu <id>` - Delete waifu from database
`.syncwaifus` - Sync waifus from JSON to DB

**📢 Communication:**
`.broadcast <msg>` - Broadcast to all users
`.gcast <msg>` - Broadcast to all groups

**📊 Statistics:**
`.bstats` - Full bot statistics
`.dbstats` - Database statistics
`.topgroups` - Top active groups

**👥 User Management:**
`.sudo add @user` - Add sudo user
`.sudo remove @user` - Remove sudo user
`.sudo list` - List sudo users
`.ban @user` - Ban user from bot
`.unban @user` - Unban user
`.banlist` - List banned users
`.resetuser @user` - Reset user data
`.userinfo @user` - View user details

**🔧 Maintenance:**
`.vacuum` - Clean database
`.backup @user` - Backup user data
"""


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == OWNER_ID or user_id in SUDO_USERS


def is_owner(user_id: int) -> bool:
    """Check if user is owner"""
    return user_id == OWNER_ID


def format_number(num: int) -> str:
    """Format large numbers"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity"""
    rarity_emojis = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "mythic": "🔴",
        "divine": "✨",
        "special": "💫",
        "limited": "🌟"
    }
    return rarity_emojis.get(rarity.lower(), "⚫")


# ═══════════════════════════════════════════════════════════════════
#  COIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["addcoins", "ac"], prefixes=COMMAND_PREFIX))
async def add_coins_cmd(client: Client, message: Message):
    """Add coins to user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    target = None
    amount = 0

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except ValueError:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except Exception:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "• `.addcoins @user <amount>`\n"
            "• Reply to user: `.addcoins <amount>`"
        )

    if amount <= 0:
        return await message.reply_text("❌ Amount must be positive!")

    # Ensure user exists
    db.get_or_create_user(target.id, target.username, target.first_name)
    
    old_balance = db.get_coins(target.id)
    success = db.add_coins(target.id, amount)
    new_balance = db.get_coins(target.id)

    if not success:
        return await message.reply_text("❌ Failed to add coins!")

    await message.reply_text(
        f"✅ **Coins Added Successfully!**\n\n"
        f"👤 **User:** {target.mention}\n"
        f"💰 **Added:** +{amount:,} coins\n"
        f"📊 **Balance:** {old_balance:,} → {new_balance:,}"
    )


@Client.on_message(filters.command(["removecoins", "rc"], prefixes=COMMAND_PREFIX))
async def remove_coins_cmd(client: Client, message: Message):
    """Remove coins from user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    target = None
    amount = 0

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except ValueError:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except Exception:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "• `.removecoins @user <amount>`\n"
            "• Reply to user: `.removecoins <amount>`"
        )

    if amount <= 0:
        return await message.reply_text("❌ Amount must be positive!")

    old_balance = db.get_coins(target.id)
    
    if old_balance < amount:
        return await message.reply_text(
            f"❌ **Insufficient Balance!**\n\n"
            f"👤 **User:** {target.mention}\n"
            f"💰 **Current:** {old_balance:,} coins\n"
            f"❌ **Requested:** {amount:,} coins"
        )

    success = db.remove_coins(target.id, amount)
    new_balance = db.get_coins(target.id)

    if not success:
        return await message.reply_text("❌ Failed to remove coins!")

    await message.reply_text(
        f"✅ **Coins Removed Successfully!**\n\n"
        f"👤 **User:** {target.mention}\n"
        f"💸 **Removed:** -{amount:,} coins\n"
        f"📊 **Balance:** {old_balance:,} → {new_balance:,}"
    )


@Client.on_message(filters.command(["setcoins", "sc"], prefixes=COMMAND_PREFIX))
async def set_coins_cmd(client: Client, message: Message):
    """Set exact coin balance for user"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    target = None
    amount = 0

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        try:
            amount = int(message.command[1]) if len(message.command) > 1 else 0
        except ValueError:
            return await message.reply_text("❌ Invalid amount!")
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[1])
            amount = int(message.command[2])
        except Exception:
            return await message.reply_text("❌ Invalid user or amount!")
    else:
        return await message.reply_text("❌ **Usage:** `.setcoins @user <amount>`")

    if amount < 0:
        return await message.reply_text("❌ Amount cannot be negative!")

    db.get_or_create_user(target.id, target.username, target.first_name)
    old_balance = db.get_coins(target.id)
    success = db.set_coins(target.id, amount)

    if not success:
        return await message.reply_text("❌ Failed to set coins!")

    await message.reply_text(
        f"✅ **Coins Set Successfully!**\n\n"
        f"👤 **User:** {target.mention}\n"
        f"📊 **Balance:** {old_balance:,} → {amount:,}"
    )


# ═══════════════════════════════════════════════════════════════════
#  WAIFU MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["addwaifu", "aw"], prefixes=COMMAND_PREFIX))
async def add_waifu_cmd(client: Client, message: Message):
    """Add new waifu to database"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply_text(
            "❌ **Reply to a message with waifu JSON!**\n\n"
            "**Format:**\n"
            "```json\n"
            "{\n"
            '  "name": "Waifu Name",\n'
            '  "anime": "Anime Name",\n'
            '  "rarity": "Legendary",\n'
            '  "image": "image_url"\n'
            "}\n"
            "```"
        )

    try:
        waifu_data = json.loads(message.reply_to_message.text)
    except json.JSONDecodeError:
        return await message.reply_text("❌ Invalid JSON format!")

    required = ["name", "anime", "rarity"]
    missing = [f for f in required if f not in waifu_data]
    if missing:
        return await message.reply_text(f"❌ Missing fields: `{', '.join(missing)}`")

    waifus = load_waifus()
    max_id = max([w.get("id", 0) for w in waifus], default=0)
    waifu_data["id"] = max_id + 1
    waifu_data["added_by"] = message.from_user.id
    waifu_data["added_at"] = datetime.now().isoformat()

    waifus.append(waifu_data)
    save_waifus(waifus)

    # Also sync to MongoDB
    db.upsert_waifu(waifu_data)

    rarity_emoji = get_rarity_emoji(waifu_data['rarity'])

    await message.reply_text(
        f"✅ **Waifu Added Successfully!**\n\n"
        f"🆔 **ID:** `{waifu_data['id']}`\n"
        f"👤 **Name:** {waifu_data['name']}\n"
        f"🎬 **Anime:** {waifu_data['anime']}\n"
        f"{rarity_emoji} **Rarity:** {waifu_data['rarity']}\n"
        f"🖼️ **Image:** {'✅' if waifu_data.get('image') else '❌'}"
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
    except ValueError:
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
    
    # Also remove from MongoDB
    db.delete_waifu_from_registry(waifu_id)

    await message.reply_text(
        f"🗑️ **Waifu Deleted!**\n\n"
        f"🆔 **ID:** `{removed['id']}`\n"
        f"👤 **Name:** {removed['name']}\n"
        f"🎬 **Anime:** {removed.get('anime', 'Unknown')}"
    )


@Client.on_message(filters.command(["syncwaifus", "sync"], prefixes=COMMAND_PREFIX))
async def sync_waifus_cmd(client: Client, message: Message):
    """Sync waifus from JSON to MongoDB"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    status_msg = await message.reply_text("🔄 Syncing waifus to database...")

    try:
        count = db.sync_waifus_from_json()
        await status_msg.edit_text(
            f"✅ **Sync Complete!**\n\n"
            f"📦 **Synced:** {count} waifus"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Sync failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
#  BROADCAST
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["broadcast", "bc"], prefixes=COMMAND_PREFIX))
async def broadcast_cmd(client: Client, message: Message):
    """Broadcast message to all users"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    broadcast_text = None
    broadcast_msg = None

    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
    elif len(message.command) > 1:
        broadcast_text = message.text.split(None, 1)[1]
    else:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "• `.broadcast <message>`\n"
            "• Reply to a message: `.broadcast`"
        )

    all_users = db.get_all_users()
    total = len(all_users)

    if total == 0:
        return await message.reply_text("❌ No users to broadcast to!")

    status_msg = await message.reply_text(
        f"📤 **Broadcasting...**\n\n"
        f"👥 **Total Users:** {total:,}\n"
        f"⏳ **Progress:** 0%"
    )

    success = 0
    failed = 0
    blocked = 0

    for i, user in enumerate(all_users, 1):
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

            # Update progress every 50 users
            if i % 50 == 0:
                progress = int((i / total) * 100)
                try:
                    await status_msg.edit_text(
                        f"📤 **Broadcasting...**\n\n"
                        f"👥 **Total:** {total:,}\n"
                        f"✅ **Sent:** {success:,}\n"
                        f"❌ **Failed:** {failed:,}\n"
                        f"⏳ **Progress:** {progress}%"
                    )
                except:
                    pass

            # Avoid flood
            await asyncio.sleep(0.05)

        except Exception as e:
            if "blocked" in str(e).lower():
                blocked += 1
            failed += 1

    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"👥 **Total Users:** {total:,}\n"
        f"📤 **Sent:** {success:,}\n"
        f"🚫 **Blocked:** {blocked:,}\n"
        f"❌ **Failed:** {failed - blocked:,}\n\n"
        f"📊 **Success Rate:** {(success/total*100):.1f}%"
    )


@Client.on_message(filters.command(["gcast", "groupcast"], prefixes=COMMAND_PREFIX))
async def group_broadcast_cmd(client: Client, message: Message):
    """Broadcast to all groups"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    broadcast_text = None
    broadcast_msg = None

    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
    elif len(message.command) > 1:
        broadcast_text = message.text.split(None, 1)[1]
    else:
        return await message.reply_text("❌ **Usage:** `.gcast <message>` or reply to a message")

    all_groups = db.get_all_groups()
    total = len(all_groups)

    if total == 0:
        return await message.reply_text("❌ No groups to broadcast to!")

    status_msg = await message.reply_text(f"📤 Broadcasting to {total} groups...")

    success = 0
    failed = 0

    for group in all_groups:
        try:
            chat_id = group.get("chat_id")
            if not chat_id:
                failed += 1
                continue

            if broadcast_msg:
                await broadcast_msg.copy(chat_id)
            else:
                await client.send_message(chat_id, broadcast_text)
            success += 1
            await asyncio.sleep(0.1)

        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **Group Broadcast Complete!**\n\n"
        f"👥 **Total Groups:** {total:,}\n"
        f"📤 **Sent:** {success:,}\n"
        f"❌ **Failed:** {failed:,}"
    )


# ═══════════════════════════════════════════════════════════════════
#  STATISTICS - FULLY FIXED
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["botstats", "bstats", "stats"], prefixes=COMMAND_PREFIX))
async def bot_stats_cmd(client: Client, message: Message):
    """View comprehensive bot statistics"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    status_msg = await message.reply_text("📊 **Gathering statistics...**")

    try:
        # ═══ USER STATS ═══
        total_users = db.get_total_users()
        active_24h = db.get_active_users_count(hours=24)
        active_7d = db.get_active_users_count(hours=168)
        banned_users = db.get_banned_users_count()
        
        # Get new users today
        uptime_stats = db.get_bot_uptime_stats()
        new_today = uptime_stats.get("new_users_today", 0)

        # ═══ GROUP STATS ═══
        total_groups = db.get_total_groups()
        active_groups_24h = db.get_active_groups_count(hours=24)
        active_groups_7d = db.get_active_groups_count(hours=168)
        
        # Get top groups for extra info
        top_groups = db.get_top_groups(limit=3)

        # ═══ WAIFU STATS ═══
        waifus = load_waifus()
        total_available = len(waifus)
        total_collected = db.get_total_collected_waifus()
        unique_collectors = db.get_unique_collectors_count()
        waifus_in_registry = db.get_total_waifus_in_registry()

        # ═══ ECONOMY STATS ═══
        total_coins = db.get_total_coins_in_circulation()

        # ═══ GAMEPLAY STATS ═══
        global_stats = db.get_global_stats()
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
        total_games = total_smashes + total_passes
        smash_rate = (total_smashes / total_games * 100) if total_games > 0 else 0

        # ═══ RARITY DISTRIBUTION ═══
        rarity_stats = db.get_rarity_distribution()

        # ═══ BUILD THE MESSAGE ═══
        text = f"""
╔══════════════════════════════════╗
║     📊 **BOT STATISTICS**        ║
╚══════════════════════════════════╝

┌─────────────────────────────────┐
│         👥 **USERS**            │
└─────────────────────────────────┘
│ 📊 Total Users    : **{total_users:,}**
│ 🟢 Active (24h)   : **{active_24h:,}**
│ 📅 Active (7d)    : **{active_7d:,}**
│ 🆕 New Today      : **{new_today:,}**
│ 🚫 Banned         : **{banned_users:,}**
└─────────────────────────────────┘

┌─────────────────────────────────┐
│         💬 **GROUPS**           │
└─────────────────────────────────┘
│ 📊 Total Groups   : **{total_groups:,}**
│ 🟢 Active (24h)   : **{active_groups_24h:,}**
│ 📅 Active (7d)    : **{active_groups_7d:,}**
└─────────────────────────────────┘

┌─────────────────────────────────┐
│         🎴 **WAIFUS**           │
└─────────────────────────────────┘
│ 📦 Available      : **{total_available:,}**
│ 🗃️ In Registry    : **{waifus_in_registry:,}**
│ 🎴 Collected      : **{total_collected:,}**
│ 👥 Collectors     : **{unique_collectors:,}**
└─────────────────────────────────┘

┌─────────────────────────────────┐
│         🎮 **GAMEPLAY**         │
└─────────────────────────────────┘
│ 💕 Smashes        : **{format_number(total_smashes)}**
│ 💔 Passes         : **{format_number(total_passes)}**
│ 🎯 Total Games    : **{format_number(total_games)}**
│ 📈 Smash Rate     : **{smash_rate:.1f}%**
└─────────────────────────────────┘

┌─────────────────────────────────┐
│         💰 **ECONOMY**          │
└─────────────────────────────────┘
│ 💵 Total Coins    : **{format_number(total_coins)}**
│ 📊 Avg/User       : **{format_number(total_coins // max(total_users, 1))}**
└─────────────────────────────────┘

┌─────────────────────────────────┐
│      📈 **RARITY BREAKDOWN**    │
└─────────────────────────────────┘"""

        # Add rarity distribution
        if rarity_stats:
            for rarity, count in sorted(rarity_stats.items(), key=lambda x: x[1], reverse=True):
                emoji = get_rarity_emoji(rarity)
                percentage = (count / max(total_collected, 1)) * 100
                text += f"\n│ {emoji} {rarity.title():12} : **{count:,}** ({percentage:.1f}%)"
        else:
            text += "\n│ No data available"

        text += "\n└─────────────────────────────────┘"

        # Add top groups if available
        if top_groups:
            text += "\n\n┌─────────────────────────────────┐"
            text += "\n│       🏆 **TOP GROUPS**         │"
            text += "\n└─────────────────────────────────┘"
            for i, group in enumerate(top_groups, 1):
                medal = ["🥇", "🥈", "🥉"][i-1]
                title = group.get("title", "Unknown")[:20]
                spawns = group.get("spawn_count", 0)
                text += f"\n│ {medal} {title}: **{spawns:,}** spawns"
            text += "\n└─────────────────────────────────┘"

        # Add timestamp
        text += f"\n\n⏰ **Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await status_msg.edit_text(text)

    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Error fetching stats!**\n\n"
            f"```{str(e)}```"
        )


@Client.on_message(filters.command(["dbstats", "database"], prefixes=COMMAND_PREFIX))
async def db_stats_cmd(client: Client, message: Message):
    """View database statistics"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    status_msg = await message.reply_text("🔍 Analyzing database...")

    try:
        db_size = db.get_database_size()
        debug_data = db.debug_check_data()

        text = "🗄️ **Database Statistics**\n\n"
        text += "**Collection Sizes:**\n"

        total_docs = 0
        total_size = 0

        for name, stats in db_size.items():
            if isinstance(stats, dict):
                count = stats.get("count", 0)
                size = stats.get("size", 0)
                total_docs += count
                total_size += size
                size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                text += f"• **{name}:** {count:,} docs ({size_str})\n"

        text += f"\n📊 **Total:** {total_docs:,} documents"
        text += f"\n💾 **Size:** {total_size/1024/1024:.2f}MB"

        # Additional debug info
        text += f"\n\n**Quick Stats:**"
        text += f"\n• Users with coins: {debug_data.get('users_with_coins', 0):,}"
        text += f"\n• Users with wins: {debug_data.get('users_with_wins', 0):,}"
        text += f"\n• Banned users: {debug_data.get('banned_users', 0):,}"

        await status_msg.edit_text(text)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")


@Client.on_message(filters.command(["topgroups", "tg"], prefixes=COMMAND_PREFIX))
async def top_groups_cmd(client: Client, message: Message):
    """View top groups"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    top_groups = db.get_top_groups(limit=15)

    if not top_groups:
        return await message.reply_text("📭 No group data available!")

    text = "🏆 **Top Groups by Activity**\n\n"

    for i, group in enumerate(top_groups, 1):
        if i <= 3:
            medal = ["🥇", "🥈", "🥉"][i-1]
        else:
            medal = f"{i}."

        title = group.get("title", "Unknown Group")
        if len(title) > 25:
            title = title[:22] + "..."

        spawns = group.get("spawn_count", 0)
        messages = group.get("message_count", 0)
        
        text += f"{medal} **{title}**\n"
        text += f"    └ 🎴 {spawns:,} spawns | 💬 {messages:,} msgs\n\n"

    total = db.get_total_groups()
    text += f"\n📊 **Total Groups:** {total:,}"

    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["sudo"], prefixes=COMMAND_PREFIX))
async def sudo_cmd(client: Client, message: Message):
    """Manage sudo users"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    if len(message.command) < 2:
        return await message.reply_text(
            "👑 **Sudo Management**\n\n"
            "`.sudo add @user` - Add sudo\n"
            "`.sudo remove @user` - Remove sudo\n"
            "`.sudo list` - List sudos"
        )

    action = message.command[1].lower()

    if action == "list":
        if not SUDO_USERS:
            return await message.reply_text("📭 No sudo users configured!")

        text = "👑 **Sudo Users:**\n\n"
        for i, user_id in enumerate(SUDO_USERS, 1):
            try:
                user = await client.get_users(user_id)
                text += f"{i}. {user.mention} (`{user_id}`)\n"
            except:
                text += f"{i}. Unknown (`{user_id}`)\n"

        return await message.reply_text(text)

    # Get target user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) >= 3:
        try:
            target = await client.get_users(message.command[2])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ Specify a user!")

    if action == "add":
        if target.id == OWNER_ID:
            return await message.reply_text("❌ Owner is already super admin!")
        if target.id in SUDO_USERS:
            return await message.reply_text("❌ Already a sudo user!")

        SUDO_USERS.append(target.id)
        await message.reply_text(f"✅ Added {target.mention} as sudo!")

    elif action == "remove":
        if target.id not in SUDO_USERS:
            return await message.reply_text("❌ Not a sudo user!")

        SUDO_USERS.remove(target.id)
        await message.reply_text(f"✅ Removed {target.mention} from sudo!")


@Client.on_message(filters.command(["ban", "banuser"], prefixes=COMMAND_PREFIX))
async def ban_user_cmd(client: Client, message: Message):
    """Ban user from bot"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    reason = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
            if len(message.command) > 2:
                reason = " ".join(message.command[2:])
        except:
            return await message.reply_text("❌ User not found!")
    else:
        return await message.reply_text("❌ Specify a user!")

    if target.id == OWNER_ID:
        return await message.reply_text("❌ Can't ban the owner!")
    if target.id in SUDO_USERS:
        return await message.reply_text("❌ Can't ban sudo users!")

    db.ban_user(target.id, reason)

    text = f"🔨 **User Banned!**\n\n👤 **User:** {target.mention}"
    if reason:
        text += f"\n📝 **Reason:** {reason}"

    await message.reply_text(text)


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

    if not db.is_user_banned(target.id):
        return await message.reply_text("❌ User is not banned!")

    db.unban_user(target.id)
    await message.reply_text(f"✅ Unbanned {target.mention}!")


@Client.on_message(filters.command(["banlist", "banned"], prefixes=COMMAND_PREFIX))
async def banlist_cmd(client: Client, message: Message):
    """List banned users"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    banned = db.get_banned_users()

    if not banned:
        return await message.reply_text("📭 No banned users!")

    text = "🚫 **Banned Users:**\n\n"

    for i, user in enumerate(banned[:20], 1):
        user_id = user.get("user_id")
        username = user.get("username") or "Unknown"
        reason = user.get("ban_reason") or "No reason"
        text += f"{i}. `{user_id}` (@{username})\n   └ {reason}\n\n"

    if len(banned) > 20:
        text += f"\n_...and {len(banned) - 20} more_"

    text += f"\n\n📊 **Total Banned:** {len(banned)}"

    await message.reply_text(text)


@Client.on_message(filters.command(["resetuser", "reset"], prefixes=COMMAND_PREFIX))
async def reset_user_cmd(client: Client, message: Message):
    """Reset user data completely"""
    if not is_owner(message.from_user.id):
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

    # Confirmation
    confirm_msg = await message.reply_text(
        f"⚠️ **Are you sure?**\n\n"
        f"This will DELETE all data for {target.mention}:\n"
        f"• Coins\n"
        f"• Collection\n"
        f"• Stats\n"
        f"• Trades\n\n"
        f"Reply with `CONFIRM` within 30 seconds to proceed."
    )

    try:
        response = await client.listen(
            message.chat.id,
            filters=filters.user(message.from_user.id) & filters.text,
            timeout=30
        )
        if response.text.upper() != "CONFIRM":
            return await message.reply_text("❌ Reset cancelled!")
    except:
        return await message.reply_text("❌ Timeout! Reset cancelled.")

    db.reset_user(target.id)
    await message.reply_text(f"🗑️ **Reset Complete!**\n\nAll data for {target.mention} has been deleted!")


@Client.on_message(filters.command(["userinfo", "ui"], prefixes=COMMAND_PREFIX))
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
        return await message.reply_text("❌ Specify a user!")

    user_data = db.get_user(target.id)

    if not user_data:
        return await message.reply_text("❌ User not in database!")

    collection_count = db.get_collection_count(target.id)
    rarity_dist = db.get_user_rarity_distribution(target.id)

    text = f"""
👤 **User Info: {target.first_name}**

**📋 Basic Info:**
• ID: `{target.id}`
• Username: @{target.username or 'None'}
• Banned: {'🚫 Yes' if user_data.get('banned') else '✅ No'}

**💰 Economy:**
• Coins: {user_data.get('coins', 0):,}
• Earned: {user_data.get('total_earned', 0):,}
• Spent: {user_data.get('total_spent', 0):,}

**🎮 Stats:**
• Smashes: {user_data.get('total_smash', 0):,}
• Passes: {user_data.get('total_pass', 0):,}
• Wins: {user_data.get('total_wins', 0):,}
• Streak: {user_data.get('daily_streak', 0)} days

**🎴 Collection:**
• Total: {collection_count:,} waifus
"""

    if rarity_dist:
        text += "\n**📊 Rarity Breakdown:**\n"
        for rarity, count in rarity_dist.items():
            emoji = get_rarity_emoji(rarity)
            text += f"• {emoji} {rarity.title()}: {count}\n"

    # Timestamps
    created = user_data.get("created_at")
    last_active = user_data.get("last_active")

    if created:
        text += f"\n📅 **Joined:** {created.strftime('%Y-%m-%d')}"
    if last_active:
        text += f"\n⏰ **Last Active:** {last_active.strftime('%Y-%m-%d %H:%M')}"

    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  MAINTENANCE
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["vacuum", "cleanup"], prefixes=COMMAND_PREFIX))
async def vacuum_cmd(client: Client, message: Message):
    """Clean up database"""
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command!")

    status_msg = await message.reply_text("🧹 Cleaning database...")

    try:
        results = db.vacuum_database()

        text = "✅ **Database Cleanup Complete!**\n\n"
        for key, value in results.items():
            text += f"• {key.replace('_', ' ').title()}: {value}\n"

        await status_msg.edit_text(text)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")


@Client.on_message(filters.command(["backup"], prefixes=COMMAND_PREFIX))
async def backup_cmd(client: Client, message: Message):
    """Backup user data"""
    if not is_owner(message.from_user.id):
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

    backup_data = db.backup_user_data(target.id)

    if "error" in backup_data:
        return await message.reply_text(f"❌ Error: {backup_data['error']}")

    # Save to file
    filename = f"backup_{target.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, default=str)

    await message.reply_document(
        filename,
        caption=f"📦 **Backup for {target.mention}**\n\nContains user data, collection, and trade history."
    )

    os.remove(filename)
