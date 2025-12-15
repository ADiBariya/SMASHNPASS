# modules/send.py - Send Waifus to Users (Owner/Sudo Only)

from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from helpers import get_waifu_manager
import config

# Module info
__MODULE__ = "𝐒𝐞𝐧𝐝"
__HELP__ = """
🎁 **Send Waifus (Owner/Sudo Only)**

**Commands:**
/send <user> <waifu_id> - Send specific waifu to user
/sendall <from_user> <to_user> - Transfer all waifus
/sendrandom <user> [rarity] - Send random waifu
/takewaifu <user> <waifu_id> - Remove waifu from user
/clearwaifus <user> - Clear all waifus from user
/waifulist - List all available waifus

**User can be:**
• User ID: `123456789`
• Username: `@username`
• Reply to user's message

**Examples:**
`/send 123456789 5` - Send waifu ID 5
`/send @username 5` - Send by username
`/send 5` (reply to user) - Send by reply
"""


# ═══════════════════════════════════════════════════════════════════
#  Permission Check
# ═══════════════════════════════════════════════════════════════════

def is_authorized(user_id: int) -> bool:
    """Check if user is owner or sudo"""
    owner_id = getattr(config, 'OWNER_ID', 0)
    sudo_users = getattr(config, 'SUDO_USERS', [])
    
    return user_id == owner_id or user_id in sudo_users


# ═══════════════════════════════════════════════════════════════════
#  Helper: Get User ID from various inputs
# ═══════════════════════════════════════════════════════════════════

async def get_user_id(client: Client, message: Message, user_input: str = None) -> tuple:
    """
    Get user_id from:
    1. Reply to message
    2. Username (@username)
    3. User ID (numbers)
    
    Returns: (user_id, error_message)
    """
    
    # Method 1: Reply to message
    if message.reply_to_message and not user_input:
        reply_user = message.reply_to_message.from_user
        if reply_user:
            return reply_user.id, None
        return None, "❌ Cannot get user from replied message!"
    
    if not user_input:
        return None, "❌ Please provide user ID, @username, or reply to a user!"
    
    # Method 2: Username (@username)
    if user_input.startswith("@"):
        try:
            user = await client.get_users(user_input)
            return user.id, None
        except Exception as e:
            return None, f"❌ User `{user_input}` not found!"
    
    # Method 3: User ID (numbers)
    try:
        user_id = int(user_input)
        return user_id, None
    except ValueError:
        # Maybe username without @
        try:
            user = await client.get_users(user_input)
            return user.id, None
        except:
            return None, f"❌ Invalid user: `{user_input}`"


# ═══════════════════════════════════════════════════════════════════
#  /send Command - Send Specific Waifu
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["send", "sendwaifu"]))
async def send_waifu_command(client: Client, message: Message):
    """Send a specific waifu to a user"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    args = message.text.split()[1:]
    
    target_user_id = None
    waifu_id = None
    
    # Case 1: Reply + waifu_id
    if message.reply_to_message:
        if len(args) < 1:
            await message.reply_text(
                "**Usage (Reply):** `/send <waifu_id>`\n\n"
                "**Example:** Reply to user and send `/send 5`"
            )
            return
        
        target_user_id, error = await get_user_id(client, message)
        if error:
            await message.reply_text(error)
            return
        
        try:
            waifu_id = int(args[0])
        except ValueError:
            await message.reply_text("❌ Invalid waifu ID!")
            return
    
    # Case 2: user + waifu_id
    else:
        if len(args) < 2:
            await message.reply_text(
                "**Usage:** `/send <user> <waifu_id>`\n\n"
                "**Examples:**\n"
                "• `/send 123456789 5` - By user ID\n"
                "• `/send @username 5` - By username\n"
                "• `/send 5` (reply to user) - By reply"
            )
            return
        
        target_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(error)
            return
        
        try:
            waifu_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid waifu ID!")
            return
    
    # Get waifu manager
    try:
        wm = get_waifu_manager()
    except Exception as e:
        await message.reply_text(f"❌ Error loading waifus: {e}")
        return
    
    # Find the waifu
    waifu = None
    all_waifus = wm.get_all_waifus() if hasattr(wm, 'waifus') else []
    
    for w in all_waifus:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        await message.reply_text(f"❌ Waifu with ID `{waifu_id}` not found!")
        return
    
    # Ensure target user exists
    try:
        db.get_or_create_user(target_user_id, None, f"User_{target_user_id}")
    except:
        pass
    
    # Add waifu to user's collection
    try:
        db.add_waifu_to_collection(target_user_id, waifu)
    except Exception as e:
        await message.reply_text(f"❌ Error adding waifu: {e}")
        return
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    
    await message.reply_text(
        f"✅ **Waifu Sent Successfully!**\n\n"
        f"{rarity_emoji} **{waifu.get('name')}**\n"
        f"📺 Anime: {waifu.get('anime')}\n"
        f"💎 Rarity: {waifu.get('rarity', 'common').title()}\n\n"
        f"👤 Sent to: `{target_user_id}`"
    )
    
    print(f"🎁 [SEND] {user.first_name} sent waifu {waifu.get('name')} to {target_user_id}")


# ═══════════════════════════════════════════════════════════════════
#  /sendall Command - Transfer All Waifus
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["sendall", "transferall"]))
async def send_all_waifus_command(client: Client, message: Message):
    """Transfer all waifus from one user to another"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    args = message.text.split()[1:]
    
    # Case 1: Reply + to_user (transfer FROM replied user TO specified user)
    if message.reply_to_message:
        if len(args) < 1:
            await message.reply_text(
                "**Usage (Reply):** `/sendall <to_user>`\n\n"
                "Reply to source user and specify destination.\n"
                "**Example:** Reply to user and send `/sendall @newowner`"
            )
            return
        
        from_user_id, error = await get_user_id(client, message)
        if error:
            await message.reply_text(error)
            return
        
        to_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(error)
            return
    
    # Case 2: from_user + to_user
    else:
        if len(args) < 2:
            await message.reply_text(
                "**Usage:** `/sendall <from_user> <to_user>`\n\n"
                "**Examples:**\n"
                "• `/sendall 111 222` - By user IDs\n"
                "• `/sendall @user1 @user2` - By usernames\n"
                "• `/sendall @user2` (reply to user1) - By reply"
            )
            return
        
        from_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(f"From user error: {error}")
            return
        
        to_user_id, error = await get_user_id(client, message, args[1])
        if error:
            await message.reply_text(f"To user error: {error}")
            return
    
    if from_user_id == to_user_id:
        await message.reply_text("❌ Cannot transfer to the same user!")
        return
    
    # Get source user's collection
    try:
        from_user = db.get_or_create_user(from_user_id, None, f"User_{from_user_id}")
        source_collection = from_user.get("collection", [])
    except Exception as e:
        await message.reply_text(f"❌ Error getting source user: {e}")
        return
    
    if not source_collection:
        await message.reply_text(f"❌ User `{from_user_id}` has no waifus!")
        return
    
    # Ensure target user exists
    try:
        db.get_or_create_user(to_user_id, None, f"User_{to_user_id}")
    except:
        pass
    
    # Transfer each waifu
    transferred = 0
    
    for waifu in source_collection:
        try:
            db.add_waifu_to_collection(to_user_id, waifu)
            transferred += 1
        except:
            pass
    
    # Clear source user's collection
    try:
        db.users.update_one(
            {"user_id": from_user_id},
            {"$set": {"collection": []}}
        )
    except Exception as e:
        await message.reply_text(f"⚠️ Transferred but couldn't clear source: {e}")
        return
    
    await message.reply_text(
        f"✅ **Transfer Complete!**\n\n"
        f"📦 Transferred: **{transferred}** waifus\n"
        f"👤 From: `{from_user_id}`\n"
        f"👤 To: `{to_user_id}`"
    )
    
    print(f"🎁 [SENDALL] {user.first_name} transferred {transferred} waifus from {from_user_id} to {to_user_id}")


# ═══════════════════════════════════════════════════════════════════
#  /sendrandom Command - Send Random Waifu
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["sendrandom", "randomsend"]))
async def send_random_command(client: Client, message: Message):
    """Send a random waifu to a user"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    args = message.text.split()[1:]
    
    target_user_id = None
    target_rarity = None
    
    # Case 1: Reply (optional rarity)
    if message.reply_to_message:
        target_user_id, error = await get_user_id(client, message)
        if error:
            await message.reply_text(error)
            return
        
        if len(args) >= 1:
            target_rarity = args[0].lower()
    
    # Case 2: user + optional rarity
    else:
        if len(args) < 1:
            await message.reply_text(
                "**Usage:** `/sendrandom <user> [rarity]`\n\n"
                "**Examples:**\n"
                "• `/sendrandom 123456789` - Any random\n"
                "• `/sendrandom @username legendary` - Random legendary\n"
                "• `/sendrandom` (reply) - By reply\n\n"
                "**Rarities:** common, rare, epic, legendary"
            )
            return
        
        target_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(error)
            return
        
        if len(args) >= 2:
            target_rarity = args[1].lower()
    
    valid_rarities = ["common", "rare", "epic", "legendary"]
    
    if target_rarity and target_rarity not in valid_rarities:
        await message.reply_text(
            f"❌ Invalid rarity: `{target_rarity}`\n\n"
            f"Valid: {', '.join(valid_rarities)}"
        )
        return
    
    # Get waifu manager
    try:
        wm = get_waifu_manager()
    except Exception as e:
        await message.reply_text(f"❌ Error loading waifus: {e}")
        return
    
    # Get waifu
    import random
    all_waifus = wm.get_all_waifus() if hasattr(wm, 'waifus') else []
    
    if target_rarity:
        matching = [w for w in all_waifus if w.get("rarity", "common") == target_rarity]
        if not matching:
            await message.reply_text(f"❌ No {target_rarity} waifus available!")
            return
        waifu = random.choice(matching)
    else:
        waifu = wm.get_random_waifu()
    
    if not waifu:
        await message.reply_text("❌ No waifus available!")
        return
    
    # Ensure user exists
    try:
        db.get_or_create_user(target_user_id, None, f"User_{target_user_id}")
    except:
        pass
    
    # Add waifu
    try:
        db.add_waifu_to_collection(target_user_id, waifu)
    except Exception as e:
        await message.reply_text(f"❌ Error adding waifu: {e}")
        return
    
    rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
    
    await message.reply_text(
        f"✅ **Random Waifu Sent!**\n\n"
        f"{rarity_emoji} **{waifu.get('name')}**\n"
        f"📺 Anime: {waifu.get('anime')}\n"
        f"💎 Rarity: {waifu.get('rarity', 'common').title()}\n\n"
        f"👤 Sent to: `{target_user_id}`"
    )
    
    print(f"🎁 [SENDRANDOM] {user.first_name} sent random waifu {waifu.get('name')} to {target_user_id}")


@Client.on_message(filters.command(["takewaifu", "removewaifu"]))
async def take_waifu_command(client: Client, message: Message):
    """Remove a waifu from user's collection"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    args = message.text.split()[1:]
    
    target_user_id = None
    waifu_id = None
    
    # Case 1: Reply + waifu_id
    if message.reply_to_message:
        if len(args) < 1:
            await message.reply_text(
                "**Usage (Reply):** `/takewaifu <waifu_id>`\n\n"
                "**Example:** Reply to user and send `/takewaifu 5`"
            )
            return
        
        target_user_id, error = await get_user_id(client, message)
        if error:
            await message.reply_text(error)
            return
        
        try:
            waifu_id = int(args[0])
        except ValueError:
            await message.reply_text("❌ Invalid waifu ID!")
            return
    
    # Case 2: user + waifu_id
    else:
        if len(args) < 2:
            await message.reply_text(
                "**Usage:** `/takewaifu <user> <waifu_id>`\n\n"
                "**Examples:**\n"
                "• `/takewaifu 123456789 5` - By user ID\n"
                "• `/takewaifu @username 5` - By username\n"
                "• `/takewaifu 5` (reply) - By reply"
            )
            return
        
        target_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(error)
            return
        
        try:
            waifu_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid waifu ID!")
            return
    
    # ✅ FIX: Use db.collections instead of db.users
    try:
        # Use the database method
        success = db.remove_from_collection(target_user_id, waifu_id)
        
        if success:
            await message.reply_text(
                f"✅ **Waifu Removed!**\n\n"
                f"🗑️ Waifu ID: `{waifu_id}`\n"
                f"👤 From: `{target_user_id}`"
            )
        else:
            await message.reply_text(
                f"❌ **Waifu Not Found!**\n\n"
                f"User `{target_user_id}` doesn't have waifu ID `{waifu_id}`"
            )
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
# ═══════════════════════════════════════════════════════════════════
#  /clearwaifus Command - Clear All Waifus (FIXED)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["clearwaifus", "clearall"]))
async def clear_waifus_command(client: Client, message: Message):
    """Clear all waifus from a user"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    args = message.text.split()[1:]
    
    # Case 1: Reply
    if message.reply_to_message:
        target_user_id, error = await get_user_id(client, message)
        if error:
            await message.reply_text(error)
            return
    
    # Case 2: user argument
    else:
        if len(args) < 1:
            await message.reply_text(
                "**Usage:** `/clearwaifus <user>`\n\n"
                "**Examples:**\n"
                "• `/clearwaifus 123456789`\n"
                "• `/clearwaifus @username`\n"
                "• `/clearwaifus` (reply to user)\n\n"
                "⚠️ This will remove ALL waifus from the user!"
            )
            return
        
        target_user_id, error = await get_user_id(client, message, args[0])
        if error:
            await message.reply_text(error)
            return
    
    # ✅ FIX: Delete from 'collections' collection, NOT 'users'
    try:
        # First count how many waifus user has
        waifu_count = db.collections.count_documents({"user_id": target_user_id})
        
        if waifu_count == 0:
            await message.reply_text(
                f"ℹ️ **No Waifus to Clear!**\n\n"
                f"User `{target_user_id}` has 0 waifus."
            )
            return
        
        # Delete all waifus from collections
        result = db.collections.delete_many({"user_id": target_user_id})
        
        if result.deleted_count > 0:
            await message.reply_text(
                f"✅ **Collection Cleared!**\n\n"
                f"🗑️ Removed **{result.deleted_count}** waifus\n"
                f"👤 From: `{target_user_id}`"
            )
            print(f"🗑️ [CLEAR] {user.first_name} cleared {result.deleted_count} waifus from {target_user_id}")
        else:
            await message.reply_text(
                f"⚠️ **Nothing Cleared**\n\n"
                f"User `{target_user_id}` - deletion failed"
            )
            
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
        print(f"❌ [CLEAR ERROR] {e}")
# ═══════════════════════════════════════════════════════════════════
#  /waifulist Command - List All Waifus
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["waifulist", "allwaifus", "listwaifus"]))
async def waifu_list_command(client: Client, message: Message):
    """List all available waifus"""
    
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ Only owner and sudo users can use this command!")
        return
    
    try:
        wm = get_waifu_manager()
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
        return
    
    all_waifus = wm.get_all_waifus() if hasattr(wm, 'waifus') else []
    
    if not all_waifus:
        await message.reply_text("❌ No waifus available!")
        return
    
    # Group by rarity
    by_rarity = {"legendary": [], "epic": [], "rare": [], "common": []}
    
    for w in all_waifus:
        rarity = w.get("rarity", "common")
        if rarity in by_rarity:
            by_rarity[rarity].append(w)
    
    text = "📋 **All Waifus**\n\n"
    
    for rarity in ["legendary", "epic", "rare", "common"]:
        waifus = by_rarity[rarity]
        if waifus:
            emoji = wm.get_rarity_emoji(rarity)
            text += f"{emoji} **{rarity.title()}** ({len(waifus)})\n"
            for w in waifus[:10]:
                text += f"  • ID `{w.get('id')}` - {w.get('name')}\n"
            if len(waifus) > 10:
                text += f"  _... and {len(waifus) - 10} more_\n"
            text += "\n"
    
    text += f"**Total:** {len(all_waifus)} waifus"
    
    await message.reply_text(text)
