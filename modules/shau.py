# shau.py - Enhanced Group Tracking & Logging

from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus, ChatType
from database import db
from config import LOG_GROUP_ID
from datetime import datetime
import asyncio
import logging

# Setup logger
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  GROUP ACTIVITY TRACKER
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.group, group=-999)
async def track_group_activity(client: Client, message: Message):
    """Track all group activity for statistics"""
    try:
        if not message.chat:
            return
            
        chat = message.chat
        
        # Track/update group in database
        db.get_or_create_group(
            chat_id=chat.id,
            title=chat.title,
            username=getattr(chat, 'username', None)
        )
        
        # Increment message count
        db.increment_group_stats(chat.id, "message_count", 1)
        
        # Also track user if they sent the message
        if message.from_user:
            db.get_or_create_user(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            db.update_user_activity(message.from_user.id)
        
    except Exception as e:
        logger.error(f"Error tracking group activity: {e}")


# ═══════════════════════════════════════════════════════════════════
#  BOT ADDED/REMOVED FROM GROUPS - LOGGING
# ═══════════════════════════════════════════════════════════════════

@Client.on_chat_member_updated(filters.group)
async def on_chat_member_update(client: Client, update: ChatMemberUpdated):
    """Log when bot is added or removed from groups"""
    try:
        # Check if the update is about the bot itself
        if update.new_chat_member and update.new_chat_member.user.is_self:
            old_status = update.old_chat_member.status if update.old_chat_member else None
            new_status = update.new_chat_member.status
            
            chat = update.chat
            added_by = update.from_user
            
            # Bot was added to group
            if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
                if old_status in [None, ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                    await handle_bot_added(client, chat, added_by)
            
            # Bot was removed/kicked from group
            elif new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                if old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
                    await handle_bot_removed(client, chat, added_by)
                    
    except Exception as e:
        logger.error(f"Error in chat member update: {e}")


async def handle_bot_added(client: Client, chat, added_by):
    """Handle when bot is added to a group"""
    try:
        # Get chat member count
        try:
            member_count = await client.get_chat_members_count(chat.id)
        except:
            member_count = "Unknown"
        
        # Get chat info
        chat_type = "Supergroup" if chat.type == ChatType.SUPERGROUP else "Group"
        chat_username = f"@{chat.username}" if chat.username else "Private"
        
        # Save group to database
        db.get_or_create_group(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username
        )
        
        # Create sexy log message 😏
        log_message = f"""
╔══════════════════════════════════════╗
║  🎉 **BOT ADDED TO NEW GROUP!**      ║
╚══════════════════════════════════════╝

💬 **Group Info:**
┌─────────────────────────────────────
│ 📛 **Name:** {chat.title}
│ 🆔 **ID:** `{chat.id}`
│ 🔗 **Username:** {chat_username}
│ 📊 **Type:** {chat_type}
│ 👥 **Members:** {member_count:,}
└─────────────────────────────────────

👤 **Added By:**
┌─────────────────────────────────────
│ 📛 **Name:** {added_by.first_name} {added_by.last_name or ''}
│ 🆔 **ID:** `{added_by.id}`
│ 🔗 **Username:** @{added_by.username or 'None'}
└─────────────────────────────────────

⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔥 _Let's get this party started!_ 🔥
"""
        
        # Send to log group
        if LOG_GROUP_ID:
            await client.send_message(LOG_GROUP_ID, log_message)
            logger.info(f"Bot added to group: {chat.title} ({chat.id})")
        
        # Send welcome message to the group
        welcome_msg = f"""
🎉 **Thanks for adding me!**

Hey everyone! I'm your new Waifu Bot! 💕

**Quick Start:**
• Use `/help` to see all commands
• Play `/smash` or `/pass` game
• Collect waifus and compete!

**Admin:** Make sure I have permission to send messages!

_Let the waifu collecting begin!_ ✨
"""
        try:
            await client.send_message(chat.id, welcome_msg)
        except Exception as e:
            logger.warning(f"Couldn't send welcome to {chat.id}: {e}")
            
    except Exception as e:
        logger.error(f"Error handling bot added: {e}")


async def handle_bot_removed(client: Client, chat, removed_by):
    """Handle when bot is removed from a group"""
    try:
        # Update database - mark group as inactive
        db.mark_group_inactive(chat.id)
        
        removed_by_info = "Unknown"
        if removed_by:
            removed_by_info = f"{removed_by.first_name} (@{removed_by.username or 'None'}) [`{removed_by.id}`]"
        
        # Create log message
        log_message = f"""
╔══════════════════════════════════════╗
║  😢 **BOT REMOVED FROM GROUP**       ║
╚══════════════════════════════════════╝

💬 **Group Info:**
┌─────────────────────────────────────
│ 📛 **Name:** {chat.title}
│ 🆔 **ID:** `{chat.id}`
│ 🔗 **Username:** @{chat.username or 'Private'}
└─────────────────────────────────────

👤 **Removed By:** {removed_by_info}

⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

😔 _Another one bites the dust..._
"""
        
        # Send to log group
        if LOG_GROUP_ID:
            await client.send_message(LOG_GROUP_ID, log_message)
            logger.info(f"Bot removed from group: {chat.title} ({chat.id})")
            
    except Exception as e:
        logger.error(f"Error handling bot removed: {e}")


# ═══════════════════════════════════════════════════════════════════
#  STARTUP GROUP SCANNER
# ═══════════════════════════════════════════════════════════════════

async def scan_all_groups(client: Client):
    """
    Scan all dialogs to find groups bot is in.
    Call this on startup!
    """
    logger.info("🔍 Starting group scan...")
    
    groups_found = 0
    supergroups_found = 0
    errors = 0
    
    try:
        async for dialog in client.get_dialogs():
            try:
                chat = dialog.chat
                
                # Only process groups and supergroups
                if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    # Get member count if possible
                    try:
                        member_count = await client.get_chat_members_count(chat.id)
                    except:
                        member_count = 0
                    
                    # Save to database
                    db.get_or_create_group(
                        chat_id=chat.id,
                        title=chat.title,
                        username=getattr(chat, 'username', None)
                    )
                    
                    # Update member count
                    db.update_group_member_count(chat.id, member_count)
                    
                    if chat.type == ChatType.SUPERGROUP:
                        supergroups_found += 1
                    else:
                        groups_found += 1
                        
                    # Small delay to avoid flood
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                errors += 1
                logger.warning(f"Error processing dialog: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scanning dialogs: {e}")
    
    total = groups_found + supergroups_found
    logger.info(f"✅ Group scan complete! Found {total} groups ({groups_found} groups, {supergroups_found} supergroups)")
    
    # Send summary to log group
    if LOG_GROUP_ID:
        try:
            await client.send_message(
                LOG_GROUP_ID,
                f"🔍 **Startup Group Scan Complete!**\n\n"
                f"📊 **Results:**\n"
                f"• Groups: {groups_found}\n"
                f"• Supergroups: {supergroups_found}\n"
                f"• Total: {total}\n"
                f"• Errors: {errors}\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass
    
    return total


# ═══════════════════════════════════════════════════════════════════
#  MANUAL GROUP SYNC COMMAND
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["scangroups", "syncgroups"]) & filters.user([int(id) for id in [6422072438]]))  # Add your owner ID
async def scan_groups_cmd(client: Client, message: Message):
    """Manually trigger group scan"""
    status_msg = await message.reply_text("🔍 Scanning all groups... This may take a while.")
    
    try:
        total = await scan_all_groups(client)
        
        await status_msg.edit_text(
            f"✅ **Group Scan Complete!**\n\n"
            f"📊 Found and synced **{total}** groups to database."
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
#  GROUP STATS UPDATE (Periodic)
# ═══════════════════════════════════════════════════════════════════

async def update_all_group_stats(client: Client):
    """Update stats for all groups (run periodically)"""
    logger.info("📊 Updating group stats...")
    
    all_groups = db.get_all_groups()
    updated = 0
    
    for group in all_groups:
        try:
            chat_id = group.get("chat_id")
            if not chat_id:
                continue
                
            # Try to get updated info
            try:
                chat = await client.get_chat(chat_id)
                member_count = await client.get_chat_members_count(chat_id)
                
                db.update_group_info(
                    chat_id=chat_id,
                    title=chat.title,
                    username=getattr(chat, 'username', None),
                    member_count=member_count
                )
                updated += 1
                
            except Exception as e:
                # Group might be inaccessible
                if "CHAT_INVALID" in str(e) or "PEER_ID_INVALID" in str(e):
                    db.mark_group_inactive(chat_id)
                    
            await asyncio.sleep(0.2)  # Avoid flood
            
        except Exception as e:
            logger.warning(f"Error updating group {group.get('chat_id')}: {e}")
            continue
    
    logger.info(f"✅ Updated stats for {updated} groups")
    return updated
