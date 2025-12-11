# shau.py - Enhanced Group Tracking, Logging & Report System

from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ChatType
from database import db
from config import LOG_GROUP_ID, OWNER_ID
from datetime import datetime
import asyncio
import logging
import random

# Setup logger
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  MODULE INFO FOR HELP
# ═══════════════════════════════════════════════════════════════════

__MODULE__ = "Report & Tracking"
__HELP__ = """
📝 **Report & Tracking Commands**

**🐛 Bug Reports:**
`/report <description>` - Report a bug or issue
• Reply to a message with `/report` to include context
• Be descriptive for faster resolution!

**📊 Group Tracking:**
`/scangroups` - Scan all groups (Owner only)
`/syncgroups` - Sync groups to database (Owner only)

**Example:**
`/report The /daily command gives 0 coins instead of reward`

✨ _Your feedback helps us improve!_ 💕
"""

# Store pending reports for tracking
pending_reports = {}

# ═══════════════════════════════════════════════════════════════════
#  SEXY REPORT SYSTEM 🔥
# ═══════════════════════════════════════════════════════════════════

def generate_report_id():
    """Generate a unique report ID"""
    return f"RPT{random.randint(10000, 99999)}"


def get_report_type_emoji(report_type: str) -> str:
    """Get emoji for report type"""
    types = {
        "bug": "🐛",
        "feature": "💡",
        "issue": "⚠️",
        "feedback": "💭",
        "other": "📝"
    }
    return types.get(report_type.lower(), "📝")


@Client.on_message(filters.command(["report", "bug", "feedback", "issue"]))
async def report_cmd(client: Client, message: Message):
    """
    Sexy report system for users to report bugs/issues
    """
    user = message.from_user
    
    if not user:
        return await message.reply_text("❌ Could not identify user!")
    
    # Get the report content
    report_text = None
    replied_msg_info = None
    
    # Check if replying to a message
    if message.reply_to_message:
        replied = message.reply_to_message
        replied_msg_info = {
            "text": replied.text or replied.caption or "[Media/Sticker]",
            "from_user": replied.from_user.first_name if replied.from_user else "Unknown",
            "message_id": replied.id
        }
        # Get additional description from command
        if len(message.command) > 1:
            report_text = message.text.split(None, 1)[1]
        else:
            report_text = "No additional description provided"
    elif len(message.command) > 1:
        report_text = message.text.split(None, 1)[1]
    else:
        return await message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║     📝 **HOW TO REPORT**         ║\n"
            "╚══════════════════════════════════╝\n\n"
            "**Usage:**\n"
            "`/report <description of the bug/issue>`\n\n"
            "**Or reply to a message:**\n"
            "`/report <additional context>`\n\n"
            "**Examples:**\n"
            "• `/report Daily command not working`\n"
            "• `/report Can't claim waifu, shows error`\n"
            "• Reply to error message + `/report`\n\n"
            "💕 _Your reports help us improve!_"
        )
    
    # Validate report length
    if len(report_text) < 10:
        return await message.reply_text(
            "❌ **Report too short!**\n\n"
            "Please provide more details about the issue.\n"
            "Minimum 10 characters required."
        )
    
    if len(report_text) > 1000:
        return await message.reply_text(
            "❌ **Report too long!**\n\n"
            "Please keep your report under 1000 characters."
        )
    
    # Generate report ID
    report_id = generate_report_id()
    
    # Determine chat info
    chat_info = "Private Chat"
    chat_id_info = message.chat.id
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat_info = message.chat.title or "Unknown Group"
        chat_id_info = message.chat.id
    
    # Store report
    pending_reports[report_id] = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "report_text": report_text,
        "replied_msg": replied_msg_info,
        "chat_id": chat_id_info,
        "chat_title": chat_info,
        "timestamp": datetime.now(),
        "status": "pending",
        "message_link": message.link if hasattr(message, 'link') else None
    }
    
    # Create sexy report message for owner/log
    report_message = f"""
╔══════════════════════════════════════════╗
║  🚨 **NEW BUG REPORT RECEIVED!**         ║
╚══════════════════════════════════════════╝

🔖 **Report ID:** `{report_id}`

┌─────────────────────────────────────────┐
│           👤 **REPORTER INFO**          │
└─────────────────────────────────────────┘
│ 📛 **Name:** {user.first_name} {user.last_name or ''}
│ 🆔 **User ID:** `{user.id}`
│ 🔗 **Username:** @{user.username or 'None'}
│ 💬 **From:** {chat_info}
│ 🆔 **Chat ID:** `{chat_id_info}`
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           📝 **REPORT DETAILS**         │
└─────────────────────────────────────────┘
{report_text}
└─────────────────────────────────────────┘"""

    # Add replied message context if exists
    if replied_msg_info:
        replied_text = replied_msg_info['text']
        if len(replied_text) > 200:
            replied_text = replied_text[:197] + "..."
        report_message += f"""

┌─────────────────────────────────────────┐
│        💬 **REPLIED MESSAGE**           │
└─────────────────────────────────────────┘
│ 👤 **From:** {replied_msg_info['from_user']}
│ 📄 **Content:** {replied_text}
└─────────────────────────────────────────┘"""

    report_message += f"""

⏰ **Reported At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔥 _Please review and take action!_ 🔥
"""

    # Create resolve buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Resolve", callback_data=f"report_resolve_{report_id}"),
            InlineKeyboardButton("🔍 Investigating", callback_data=f"report_investigate_{report_id}")
        ],
        [
            InlineKeyboardButton("💬 Reply to User", callback_data=f"report_reply_{report_id}"),
            InlineKeyboardButton("🚫 Spam/Invalid", callback_data=f"report_spam_{report_id}")
        ],
        [
            InlineKeyboardButton("📋 View User Info", callback_data=f"report_userinfo_{report_id}")
        ]
    ])
    
    # Send to owner DM
    try:
        await client.send_message(
            OWNER_ID,
            report_message,
            reply_markup=keyboard
        )
        logger.info(f"Report {report_id} sent to owner DM")
    except Exception as e:
        logger.error(f"Failed to send report to owner DM: {e}")
    
    # Send to log group
    if LOG_GROUP_ID:
        try:
            await client.send_message(
                LOG_GROUP_ID,
                report_message,
                reply_markup=keyboard
            )
            logger.info(f"Report {report_id} sent to log group")
        except Exception as e:
            logger.error(f"Failed to send report to log group: {e}")
    
    # Save to database
    try:
        db.save_report({
            "report_id": report_id,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "report_text": report_text,
            "replied_msg": replied_msg_info,
            "chat_id": chat_id_info,
            "chat_title": chat_info,
            "timestamp": datetime.now(),
            "status": "pending"
        })
    except Exception as e:
        logger.warning(f"Could not save report to DB: {e}")
    
    # Send confirmation to user
    confirm_message = f"""
╔══════════════════════════════════════╗
║  ✅ **REPORT SUBMITTED!**            ║
╚══════════════════════════════════════╝

🎫 **Your Report ID:** `{report_id}`

📝 **Issue:**
{report_text[:200]}{'...' if len(report_text) > 200 else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ **What happens next?**
• Our team will review your report
• You'll be notified when it's resolved
• Use your Report ID for follow-ups

💕 _Thank you for helping us improve!_

⏰ Submitted at: {datetime.now().strftime('%H:%M:%S')}
"""
    
    await message.reply_text(confirm_message)


# ═══════════════════════════════════════════════════════════════════
#  REPORT CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^report_resolve_"))
async def resolve_report_callback(client: Client, callback: CallbackQuery):
    """Handle report resolution"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner can resolve reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        # Try to get from database
        report_data = db.get_report(report_id) if hasattr(db, 'get_report') else None
        if not report_data:
            return await callback.answer("❌ Report not found or expired!", show_alert=True)
        pending_reports[report_id] = report_data
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    # Update status
    report["status"] = "resolved"
    report["resolved_at"] = datetime.now()
    report["resolved_by"] = callback.from_user.id
    
    # Update database
    try:
        db.update_report_status(report_id, "resolved")
    except:
        pass
    
    # Update the message
    new_text = callback.message.text + f"\n\n✅ **RESOLVED** by {callback.from_user.first_name}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Resolved", callback_data="none")],
            [InlineKeyboardButton("📤 Notify User", callback_data=f"report_notify_resolved_{report_id}")]
        ])
    )
    
    # Notify user
    try:
        await client.send_message(
            user_id,
            f"╔══════════════════════════════════════╗\n"
            f"║  ✅ **REPORT RESOLVED!**             ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"🎫 **Report ID:** `{report_id}`\n\n"
            f"Your reported issue has been resolved! ✨\n\n"
            f"If you're still experiencing problems,\n"
            f"feel free to submit a new report.\n\n"
            f"💕 _Thanks for your patience!_"
        )
    except Exception as e:
        logger.warning(f"Could not notify user about resolution: {e}")
    
    await callback.answer("✅ Report marked as resolved! User notified.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^report_investigate_"))
async def investigate_report_callback(client: Client, callback: CallbackQuery):
    """Mark report as under investigation"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner can manage reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    report["status"] = "investigating"
    user_id = report.get("user_id")
    
    # Update database
    try:
        db.update_report_status(report_id, "investigating")
    except:
        pass
    
    # Update message
    new_text = callback.message.text + f"\n\n🔍 **INVESTIGATING** - {callback.from_user.first_name}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Resolve", callback_data=f"report_resolve_{report_id}"),
                InlineKeyboardButton("🔍 Investigating", callback_data="none")
            ],
            [
                InlineKeyboardButton("💬 Reply to User", callback_data=f"report_reply_{report_id}"),
                InlineKeyboardButton("🚫 Spam/Invalid", callback_data=f"report_spam_{report_id}")
            ]
        ])
    )
    
    # Notify user
    try:
        await client.send_message(
            user_id,
            f"╔══════════════════════════════════════╗\n"
            f"║  🔍 **REPORT UNDER REVIEW!**         ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"🎫 **Report ID:** `{report_id}`\n\n"
            f"Our team is investigating your issue! 🔧\n\n"
            f"We'll notify you once it's resolved.\n\n"
            f"💕 _Thanks for your patience!_"
        )
    except:
        pass
    
    await callback.answer("🔍 Marked as investigating! User notified.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^report_spam_"))
async def spam_report_callback(client: Client, callback: CallbackQuery):
    """Mark report as spam/invalid"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner can manage reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id in pending_reports:
        pending_reports[report_id]["status"] = "spam"
    
    # Update database
    try:
        db.update_report_status(report_id, "spam")
    except:
        pass
    
    # Update message
    new_text = callback.message.text + f"\n\n🚫 **MARKED AS SPAM/INVALID**\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Spam/Invalid", callback_data="none")]
        ])
    )
    
    await callback.answer("🚫 Report marked as spam!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^report_reply_"))
async def reply_to_reporter_callback(client: Client, callback: CallbackQuery):
    """Send reply to the reporter"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner can reply!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    await callback.message.reply_text(
        f"💬 **Reply to Reporter**\n\n"
        f"Send your message now. It will be forwarded to:\n"
        f"👤 **User ID:** `{user_id}`\n"
        f"📛 **Name:** {report.get('first_name', 'Unknown')}\n\n"
        f"_Reply to this message with your response..._"
    )
    
    await callback.answer("Send your reply now!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^report_userinfo_"))
async def view_reporter_info_callback(client: Client, callback: CallbackQuery):
    """View reporter's detailed info"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner can view!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    # Get user data from database
    try:
        user_data = db.get_user(user_id)
        if user_data:
            coins = user_data.get("coins", 0)
            collection_count = db.get_collection_count(user_id)
            total_reports = db.get_user_report_count(user_id) if hasattr(db, 'get_user_report_count') else "N/A"
            
            info_text = f"""
👤 **Reporter Details**

📛 **Name:** {report.get('first_name', 'Unknown')}
🆔 **ID:** `{user_id}`
🔗 **Username:** @{report.get('username') or 'None'}

💰 **Coins:** {coins:,}
🎴 **Collection:** {collection_count}
📝 **Total Reports:** {total_reports}

📅 **Report Date:** {report.get('timestamp', 'Unknown')}
"""
            await callback.message.reply_text(info_text)
        else:
            await callback.answer("User not found in database!", show_alert=True)
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^report_notify_resolved_"))
async def notify_resolved_callback(client: Client, callback: CallbackQuery):
    """Manually notify user about resolution"""
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("❌ Only owner!", show_alert=True)
    
    report_id = callback.data.split("_")[3]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    try:
        await client.send_message(
            user_id,
            f"✅ **Your report `{report_id}` has been resolved!**\n\n"
            f"Thanks for helping us improve! 💕"
        )
        await callback.answer("✅ User notified!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Failed: {str(e)[:30]}", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  VIEW ALL REPORTS (Owner Command)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["reports", "allreports", "pendingbugs"]) & filters.user(OWNER_ID))
async def view_all_reports_cmd(client: Client, message: Message):
    """View all pending reports"""
    
    # Get from memory first
    pending = [r for r in pending_reports.values() if r.get("status") == "pending"]
    investigating = [r for r in pending_reports.values() if r.get("status") == "investigating"]
    
    if not pending and not investigating:
        return await message.reply_text(
            "📭 **No pending reports!**\n\n"
            "All clear! No bugs reported. ✨"
        )
    
    text = "╔══════════════════════════════════════╗\n"
    text += "║       📋 **PENDING REPORTS**         ║\n"
    text += "╚══════════════════════════════════════╝\n\n"
    
    if pending:
        text += "**🔴 Pending:**\n"
        for rid, report in list(pending_reports.items())[:10]:
            if report.get("status") == "pending":
                text += f"• `{rid}` - {report.get('first_name', 'Unknown')}\n"
                text += f"  └ {report.get('report_text', '')[:50]}...\n\n"
    
    if investigating:
        text += "\n**🔍 Investigating:**\n"
        for rid, report in list(pending_reports.items())[:10]:
            if report.get("status") == "investigating":
                text += f"• `{rid}` - {report.get('first_name', 'Unknown')}\n"
    
    text += f"\n📊 **Stats:**\n"
    text += f"• Pending: {len(pending)}\n"
    text += f"• Investigating: {len(investigating)}\n"
    text += f"• Total in memory: {len(pending_reports)}"
    
    await message.reply_text(text)


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

**Found a bug?** Use `/report` to let us know!

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

@Client.on_message(filters.command(["scangroups", "syncgroups"]) & filters.user(OWNER_ID))
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
