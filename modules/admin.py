from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import COMMAND_PREFIX, OWNER_ID, SUDO_USERS
from helpers.utils import load_waifus, save_waifus
import json
import os

__MODULE__ = "Admin"
__HELP__ = """
👑 **Admin Commands** (Owner Only)

`.addcoins @user <amount>` - Add coins
`.removecoins @user <amount>` - Remove coins
`.addwaifu` - Add new waifu (reply to JSON)
`.delwaifu <id>` - Delete waifu from database
`.broadcast <msg>` - Broadcast to all users
`.bstats` - Bot statistics
`.sudo add @user` - Add sudo user
`.sudo remove @user` - Remove sudo user
`.sudo list` - List sudo users
`.ban @user` - Ban user from bot
`.unban @user` - Unban user
`.resetuser @user` - Reset user data
"""


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


@Client.on_message(filters.command(["addcoins", "ac"], prefixes=COMMAND_PREFIX))
async def add_coins_cmd(client: Client, message: Message):
    """Add coins to user"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    # Get target user
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

    # Ensure user exists first
    db.get_or_create_user(target.id, target.username, target.first_name)
    
    success = db.add_coins(target.id, amount)

    if not success:
        return await message.reply_text("❌ Failed to add coins.")

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

    # Get target user
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
        return await message.reply_text("❌ Failed to remove coins (insufficient balance or user missing).")

    await message.reply_text(
        f"✅ **Coins Removed!**\n\n"
        f"**User:** {target.mention}\n"
        f"**Amount:** -{amount:,} coins"
    )


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
            '  "rarity": "Legendary",\n'
            '  "image": "image_url"\n'
            "}\n"
            "```"
        )

    try:
        waifu_data = json.loads(message.reply_to_message.text)
    except json.JSONDecodeError:
        return await message.reply_text("❌ Invalid JSON format!")

    # Validate required fields
    required = ["name", "anime", "rarity"]
    for field in required:
        if field not in waifu_data:
            return await message.reply_text(f"❌ Missing field: `{field}`")

    # Load existing waifus
    waifus = load_waifus()

    # Generate new ID
    max_id = max([w.get("id", 0) for w in waifus], default=0)
    waifu_data["id"] = max_id + 1

    # Add to waifus
    waifus.append(waifu_data)

    # Save
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

    # Find and remove waifu
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

    # Get all users (sync)
    all_users = db.get_all_users()

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


@Client.on_message(filters.command(["botstats", "bstats", "stats"], prefixes=COMMAND_PREFIX))
async def bot_stats_cmd(client: Client, message: Message):
    """View bot statistics"""
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ You're not authorized!")

    status_msg = await message.reply_text("📊 Fetching statistics...")

    try:
        # Get user stats
        total_users = db.get_total_users()
        
        # Get group stats
        total_groups = db.get_total_groups()
        
        # Get waifu stats
        waifus = load_waifus()
        total_available_waifus = len(waifus)
        
        # Get collection stats
        total_collected = db.get_total_collected_waifus()
        
        # Get unique collectors
        unique_collectors = db.get_unique_collectors_count()
        
        # Get economy stats
        total_coins = db.get_total_coins_in_circulation()
        
        # Get activity stats
        active_users_24h = db.get_active_users_count(hours=24)
        active_users_7d = db.get_active_users_count(hours=168)
        
        # Get game stats
        global_stats = db.get_global_stats()
        total_smashes = global_stats.get("total_smashes", 0)
        total_passes = global_stats.get("total_passes", 0)
        
        # Get rarity distribution
        rarity_stats = db.get_rarity_distribution()

        text = f"""
📊 **Bot Statistics**

╭─────────────────────╮
│     👥 **USERS**
╰─────────────────────╯

👤 **Total Users:** {total_users:,}
👥 **Total Groups:** {total_groups:,}
🟢 **Active (24h):** {active_users_24h:,}
📅 **Active (7d):** {active_users_7d:,}

╭─────────────────────╮
│     🎴 **WAIFUS**
╰─────────────────────╯

📦 **Available Waifus:** {total_available_waifus:,}
🎴 **Total Collected:** {total_collected:,}
👥 **Unique Collectors:** {unique_collectors:,}

╭─────────────────────╮
│     🎮 **GAMEPLAY**
╰─────────────────────╯

💕 **Total Smashes:** {total_smashes:,}
💔 **Total Passes:** {total_passes:,}

╭─────────────────────╮
│     💰 **ECONOMY**
╰─────────────────────╯

💵 **Total Coins:** {total_coins:,}

╭─────────────────────╮
│     📈 **RARITY DIST**
╰─────────────────────╯
"""
        # Add rarity distribution
        for rarity, count in rarity_stats.items():
            text += f"• **{rarity.title()}:** {count:,}\n"

        await status_msg.edit_text(text)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error fetching stats: {str(e)}")


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

    db.ban_user(target.id)

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

    db.unban_user(target.id)

    await message.reply_text(f"✅ Unbanned {target.mention}!")


@Client.on_message(filters.command(["resetuser", "reset"], prefixes=COMMAND_PREFIX))
async def reset_user_cmd(client: Client, message: Message):
    """Reset user data"""
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

    db.reset_user(target.id)

    await message.reply_text(f"🗑️ Reset all data for {target.mention}!")
