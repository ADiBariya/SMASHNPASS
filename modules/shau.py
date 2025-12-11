# shau.py - Enhanced Group Tracking, Logging & Report System

from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ChatType
from database import db
from config import LOG_GROUP_ID, OWNER_ID, SUDO_USERS
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
`/bug <description>` - Same as report
`/feedback <description>` - Send feedback
`/issue <description>` - Report an issue

• Reply to a message with `/report` to include context
• Be descriptive for faster resolution!

**📊 Group Tracking (Owner/Sudo):**
`/scangroups` - Scan all groups
`/syncgroups` - Sync groups to database
`/reports` - View all pending reports

**Example:**
`/report The /daily command gives 0 coins instead of reward`

✨ _Your feedback helps us improve!_ 💕
"""

# Store pending reports for tracking
pending_reports = {}


# ═══════════════════════════════════════════════════════════════════
#  PERMISSION HELPERS
# ═══════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """Check if user is admin (owner or sudo)"""
    return user_id == OWNER_ID or user_id in SUDO_USERS


def is_owner(user_id: int) -> bool:
    """Check if user is owner only"""
    return user_id == OWNER_ID


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


def get_priority_from_text(text: str) -> tuple:
    """Analyze report text and assign priority"""
    text_lower = text.lower()
    
    # High priority keywords
    high_priority = ["crash", "error", "broken", "not working", "bug", "critical", "urgent", "can't", "cannot", "failed", "stuck"]
    # Medium priority keywords  
    medium_priority = ["issue", "problem", "wrong", "incorrect", "missing", "slow"]
    # Low priority keywords
    low_priority = ["suggestion", "feature", "request", "would be nice", "maybe", "feedback"]
    
    for keyword in high_priority:
        if keyword in text_lower:
            return ("🔴", "High")
    
    for keyword in medium_priority:
        if keyword in text_lower:
            return ("🟡", "Medium")
    
    for keyword in low_priority:
        if keyword in text_lower:
            return ("🟢", "Low")
    
    return ("🟡", "Medium")


@Client.on_message(filters.command(["report", "bug", "feedback", "issue"]))
async def report_cmd(client: Client, message: Message):
    """
    Sexy report system for users to report bugs/issues
    """
    user = message.from_user
    
    if not user:
        return await message.reply_text("❌ Could not identify user!")
    
    # Determine report type from command
    cmd = message.command[0].lower()
    report_type_map = {
        "report": "Bug Report",
        "bug": "Bug Report", 
        "feedback": "Feedback",
        "issue": "Issue"
    }
    report_type = report_type_map.get(cmd, "Bug Report")
    
    # Get the report content
    report_text = None
    replied_msg_info = None
    
    # Check if replying to a message
    if message.reply_to_message:
        replied = message.reply_to_message
        replied_msg_info = {
            "text": replied.text or replied.caption or "[Media/Sticker]",
            "from_user": replied.from_user.first_name if replied.from_user else "Unknown",
            "from_user_id": replied.from_user.id if replied.from_user else None,
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
            "╔══════════════════════════════════════╗\n"
            "║       📝 **HOW TO REPORT**           ║\n"
            "╚══════════════════════════════════════╝\n\n"
            "**📌 Usage:**\n"
            "`/report <description of the bug/issue>`\n\n"
            "**💬 Or reply to a message:**\n"
            "`/report <additional context>`\n\n"
            "**🎯 Available Commands:**\n"
            "• `/report` - General bug report\n"
            "• `/bug` - Report a bug\n"
            "• `/feedback` - Send feedback\n"
            "• `/issue` - Report an issue\n\n"
            "**📝 Examples:**\n"
            "• `/report Daily command not working`\n"
            "• `/bug Can't claim waifu, shows error`\n"
            "• `/feedback Add more waifus please!`\n"
            "• Reply to error message + `/report`\n\n"
            "💕 _Your reports help us improve!_"
        )
    
    # Validate report length
    if len(report_text) < 10:
        return await message.reply_text(
            "❌ **Report too short!**\n\n"
            "Please provide more details about the issue.\n"
            "Minimum 10 characters required.\n\n"
            "💡 _Tip: Describe what happened, what you expected, and any error messages!_"
        )
    
    if len(report_text) > 1000:
        return await message.reply_text(
            "❌ **Report too long!**\n\n"
            "Please keep your report under 1000 characters.\n"
            "Be concise but descriptive! 📝"
        )
    
    # Generate report ID
    report_id = generate_report_id()
    
    # Get priority
    priority_emoji, priority_level = get_priority_from_text(report_text)
    
    # Determine chat info
    chat_info = "Private Chat"
    chat_id_info = message.chat.id
    chat_link = None
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat_info = message.chat.title or "Unknown Group"
        chat_id_info = message.chat.id
        if message.chat.username:
            chat_link = f"https://t.me/{message.chat.username}"
    
    # Store report
    pending_reports[report_id] = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "report_text": report_text,
        "report_type": report_type,
        "priority": priority_level,
        "replied_msg": replied_msg_info,
        "chat_id": chat_id_info,
        "chat_title": chat_info,
        "chat_link": chat_link,
        "timestamp": datetime.now(),
        "status": "pending",
        "message_link": message.link if hasattr(message, 'link') else None
    }
    
    # Create sexy report message for owner/log
    type_emoji = get_report_type_emoji(cmd)
    
    report_message = f"""
╔══════════════════════════════════════════════╗
║  🚨 **NEW {report_type.upper()} RECEIVED!**  ║
╚══════════════════════════════════════════════╝

🔖 **Report ID:** `{report_id}`
{type_emoji} **Type:** {report_type}
{priority_emoji} **Priority:** {priority_level}

┌──────────────────────────────────────────────┐
│             👤 **REPORTER INFO**             │
└──────────────────────────────────────────────┘
│ 📛 **Name:** {user.first_name} {user.last_name or ''}
│ 🆔 **User ID:** `{user.id}`
│ 🔗 **Username:** @{user.username or 'None'}
│ 💬 **From:** {chat_info}
│ 🆔 **Chat ID:** `{chat_id_info}`
│ 🔗 **Chat Link:** {chat_link or 'Private/No Link'}
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│             📝 **REPORT DETAILS**            │
└──────────────────────────────────────────────┘
{report_text}
└──────────────────────────────────────────────┘"""

    # Add replied message context if exists
    if replied_msg_info:
        replied_text = replied_msg_info['text']
        if len(replied_text) > 200:
            replied_text = replied_text[:197] + "..."
        report_message += f"""

┌──────────────────────────────────────────────┐
│          💬 **REPLIED MESSAGE CONTEXT**      │
└──────────────────────────────────────────────┘
│ 👤 **From:** {replied_msg_info['from_user']}
│ 🆔 **User ID:** `{replied_msg_info.get('from_user_id', 'Unknown')}`
│ 📄 **Content:** 
{replied_text}
└──────────────────────────────────────────────┘"""

    report_message += f"""

⏰ **Reported At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

🔥 _Please review and take action!_ 🔥
"""

    # Create resolve buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Resolve", callback_data=f"rpt_resolve_{report_id}"),
            InlineKeyboardButton("🔍 Investigating", callback_data=f"rpt_investigate_{report_id}")
        ],
        [
            InlineKeyboardButton("💬 Reply to User", callback_data=f"rpt_reply_{report_id}"),
            InlineKeyboardButton("🚫 Spam/Invalid", callback_data=f"rpt_spam_{report_id}")
        ],
        [
            InlineKeyboardButton("📋 User Info", callback_data=f"rpt_userinfo_{report_id}"),
            InlineKeyboardButton("⏫ Set Priority", callback_data=f"rpt_priority_{report_id}")
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
    
    # Send to all sudo users
    for sudo_id in SUDO_USERS:
        if sudo_id != OWNER_ID:  # Don't send duplicate to owner
            try:
                await client.send_message(
                    sudo_id,
                    report_message,
                    reply_markup=keyboard
                )
                logger.info(f"Report {report_id} sent to sudo user {sudo_id}")
            except Exception as e:
                logger.warning(f"Failed to send report to sudo {sudo_id}: {e}")
    
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
            "report_type": report_type,
            "priority": priority_level,
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
║     ✅ **REPORT SUBMITTED!**         ║
╚══════════════════════════════════════╝

🎫 **Your Report ID:** `{report_id}`
{type_emoji} **Type:** {report_type}
{priority_emoji} **Priority:** {priority_level}

📝 **Your Report:**
┌──────────────────────────────────────
{report_text[:200]}{'...' if len(report_text) > 200 else ''}
└──────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ **What happens next?**
• 📬 Our team has been notified
• 🔍 Your report will be reviewed
• 🔔 You'll get a DM when it's resolved
• 📋 Use Report ID for follow-ups

💕 _Thank you for helping us improve!_

⏰ Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    await message.reply_text(confirm_message)


# ═══════════════════════════════════════════════════════════════════
#  REPORT CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^rpt_resolve_"))
async def resolve_report_callback(client: Client, callback: CallbackQuery):
    """Handle report resolution"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can resolve reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        # Try to get from database
        try:
            report_data = db.get_report(report_id) if hasattr(db, 'get_report') else None
            if report_data:
                pending_reports[report_id] = report_data
            else:
                return await callback.answer("❌ Report not found or expired!", show_alert=True)
        except:
            return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    # Update status
    report["status"] = "resolved"
    report["resolved_at"] = datetime.now()
    report["resolved_by"] = callback.from_user.id
    report["resolved_by_name"] = callback.from_user.first_name
    
    # Update database
    try:
        db.update_report_status(report_id, "resolved", callback.from_user.id)
    except:
        pass
    
    # Update the message
    resolver_badge = "👑" if callback.from_user.id == OWNER_ID else "⭐"
    new_text = callback.message.text + f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **RESOLVED** 
{resolver_badge} By: {callback.from_user.first_name} (`{callback.from_user.id}`)
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Resolved", callback_data="none")],
            [InlineKeyboardButton("📤 Notify User Again", callback_data=f"rpt_notify_{report_id}")]
        ])
    )
    
    # Notify user
    try:
        await client.send_message(
            user_id,
            f"╔══════════════════════════════════════╗\n"
            f"║     ✅ **REPORT RESOLVED!**          ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"🎫 **Report ID:** `{report_id}`\n\n"
            f"🎉 Your reported issue has been resolved!\n\n"
            f"👤 **Resolved by:** {callback.from_user.first_name}\n"
            f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"If you're still experiencing problems,\n"
            f"feel free to submit a new report.\n\n"
            f"💕 _Thanks for your patience!_"
        )
        await callback.answer("✅ Report resolved! User notified.", show_alert=True)
    except Exception as e:
        logger.warning(f"Could not notify user about resolution: {e}")
        await callback.answer("✅ Resolved! (Couldn't notify user)", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_investigate_"))
async def investigate_report_callback(client: Client, callback: CallbackQuery):
    """Mark report as under investigation"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can manage reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    report["status"] = "investigating"
    report["investigating_by"] = callback.from_user.id
    user_id = report.get("user_id")
    
    # Update database
    try:
        db.update_report_status(report_id, "investigating", callback.from_user.id)
    except:
        pass
    
    # Update message
    investigator_badge = "👑" if callback.from_user.id == OWNER_ID else "⭐"
    new_text = callback.message.text + f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **UNDER INVESTIGATION**
{investigator_badge} By: {callback.from_user.first_name} (`{callback.from_user.id}`)
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Resolve", callback_data=f"rpt_resolve_{report_id}"),
                InlineKeyboardButton("🔍 Investigating...", callback_data="none")
            ],
            [
                InlineKeyboardButton("💬 Reply to User", callback_data=f"rpt_reply_{report_id}"),
                InlineKeyboardButton("🚫 Spam/Invalid", callback_data=f"rpt_spam_{report_id}")
            ]
        ])
    )
    
    # Notify user
    try:
        await client.send_message(
            user_id,
            f"╔══════════════════════════════════════╗\n"
            f"║   🔍 **REPORT UNDER REVIEW!**        ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"🎫 **Report ID:** `{report_id}`\n\n"
            f"🔧 Our team is investigating your issue!\n\n"
            f"👤 **Assigned to:** {callback.from_user.first_name}\n"
            f"⏰ **Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"We'll notify you once it's resolved.\n\n"
            f"💕 _Thanks for your patience!_"
        )
    except:
        pass
    
    await callback.answer("🔍 Marked as investigating! User notified.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_spam_"))
async def spam_report_callback(client: Client, callback: CallbackQuery):
    """Mark report as spam/invalid"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can manage reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id in pending_reports:
        pending_reports[report_id]["status"] = "spam"
        pending_reports[report_id]["marked_spam_by"] = callback.from_user.id
    
    # Update database
    try:
        db.update_report_status(report_id, "spam", callback.from_user.id)
    except:
        pass
    
    # Update message
    marker_badge = "👑" if callback.from_user.id == OWNER_ID else "⭐"
    new_text = callback.message.text + f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 **MARKED AS SPAM/INVALID**
{marker_badge} By: {callback.from_user.first_name}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Spam/Invalid", callback_data="none")],
            [InlineKeyboardButton("↩️ Undo", callback_data=f"rpt_undo_{report_id}")]
        ])
    )
    
    await callback.answer("🚫 Report marked as spam!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_undo_"))
async def undo_spam_callback(client: Client, callback: CallbackQuery):
    """Undo spam marking"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can manage reports!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id in pending_reports:
        pending_reports[report_id]["status"] = "pending"
    
    # Update database
    try:
        db.update_report_status(report_id, "pending")
    except:
        pass
    
    await callback.answer("↩️ Restored to pending!", show_alert=True)
    
    # Restore buttons
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Resolve", callback_data=f"rpt_resolve_{report_id}"),
                InlineKeyboardButton("🔍 Investigating", callback_data=f"rpt_investigate_{report_id}")
            ],
            [
                InlineKeyboardButton("💬 Reply to User", callback_data=f"rpt_reply_{report_id}"),
                InlineKeyboardButton("🚫 Spam/Invalid", callback_data=f"rpt_spam_{report_id}")
            ]
        ])
    )


@Client.on_callback_query(filters.regex(r"^rpt_reply_"))
async def reply_to_reporter_callback(client: Client, callback: CallbackQuery):
    """Prompt admin to reply to the reporter"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can reply!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    # Store the reply session
    pending_reports[report_id]["awaiting_reply_from"] = callback.from_user.id
    
    await callback.message.reply_text(
        f"💬 **Reply to Reporter**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 **Report ID:** `{report_id}`\n"
        f"👤 **User:** {report.get('first_name', 'Unknown')}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 **Their Report:**\n"
        f"{report.get('report_text', 'N/A')[:300]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✏️ **Reply with:** `/reply {report_id} <your message>`\n\n"
        f"_Example:_\n"
        f"`/reply {report_id} We've fixed this issue! Please try again.`"
    )
    
    await callback.answer("📝 Check below for reply instructions!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_userinfo_"))
async def view_reporter_info_callback(client: Client, callback: CallbackQuery):
    """View reporter's detailed info"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can view!", show_alert=True)
    
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
            total_smash = user_data.get("total_smash", 0)
            total_pass = user_data.get("total_pass", 0)
            total_wins = user_data.get("total_wins", 0)
            is_banned = user_data.get("banned", False)
            
            try:
                total_reports = db.get_user_report_count(user_id) if hasattr(db, 'get_user_report_count') else "N/A"
            except:
                total_reports = "N/A"
            
            # Get Telegram user info
            try:
                tg_user = await client.get_users(user_id)
                username = tg_user.username or "None"
                full_name = f"{tg_user.first_name} {tg_user.last_name or ''}".strip()
            except:
                username = report.get("username", "Unknown")
                full_name = report.get("first_name", "Unknown")
            
            info_text = f"""
╔══════════════════════════════════════╗
║        👤 **REPORTER DETAILS**       ║
╚══════════════════════════════════════╝

📛 **Name:** {full_name}
🆔 **ID:** `{user_id}`
🔗 **Username:** @{username}
🚫 **Banned:** {'Yes ⛔' if is_banned else 'No ✅'}

┌──────────────────────────────────────
│ 💰 **Economy**
├──────────────────────────────────────
│ 💵 Coins: {coins:,}
│ 🎴 Collection: {collection_count}
└──────────────────────────────────────

┌──────────────────────────────────────
│ 🎮 **Game Stats**
├──────────────────────────────────────
│ 💕 Smashes: {total_smash:,}
│ 💔 Passes: {total_pass:,}
│ 🏆 Wins: {total_wins:,}
└──────────────────────────────────────

┌──────────────────────────────────────
│ 📝 **Report History**
├──────────────────────────────────────
│ 📊 Total Reports: {total_reports}
│ 🎫 Current Report: `{report_id}`
└──────────────────────────────────────

📅 **Report Date:** {report.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}
"""
            await callback.message.reply_text(info_text)
            await callback.answer("📋 User info shown below!", show_alert=False)
        else:
            await callback.answer("❌ User not found in database!", show_alert=True)
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        await callback.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_priority_"))
async def set_priority_callback(client: Client, callback: CallbackQuery):
    """Set report priority"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can set priority!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 High", callback_data=f"rpt_setpri_high_{report_id}"),
            InlineKeyboardButton("🟡 Medium", callback_data=f"rpt_setpri_medium_{report_id}"),
            InlineKeyboardButton("🟢 Low", callback_data=f"rpt_setpri_low_{report_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="rpt_cancel")]
    ])
    
    await callback.message.reply_text(
        f"⏫ **Set Priority for Report `{report_id}`**\n\n"
        f"Select the priority level:",
        reply_markup=keyboard
    )
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^rpt_setpri_"))
async def set_priority_level_callback(client: Client, callback: CallbackQuery):
    """Actually set the priority level"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins!", show_alert=True)
    
    parts = callback.data.split("_")
    priority = parts[2]
    report_id = parts[3]
    
    priority_map = {
        "high": ("🔴", "High"),
        "medium": ("🟡", "Medium"),
        "low": ("🟢", "Low")
    }
    
    if report_id in pending_reports:
        pending_reports[report_id]["priority"] = priority_map[priority][1]
    
    await callback.message.edit_text(
        f"✅ Priority set to {priority_map[priority][0]} **{priority_map[priority][1]}** for `{report_id}`"
    )
    await callback.answer(f"Priority set to {priority_map[priority][1]}!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_notify_"))
async def notify_user_callback(client: Client, callback: CallbackQuery):
    """Manually notify user about resolution"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins!", show_alert=True)
    
    report_id = callback.data.split("_")[2]
    
    if report_id not in pending_reports:
        return await callback.answer("❌ Report not found!", show_alert=True)
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    try:
        await client.send_message(
            user_id,
            f"✅ **Update on your report `{report_id}`**\n\n"
            f"Your report has been resolved!\n"
            f"Thanks for helping us improve! 💕"
        )
        await callback.answer("✅ User notified!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Failed: {str(e)[:30]}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^rpt_cancel$"))
async def cancel_callback(client: Client, callback: CallbackQuery):
    """Cancel action"""
    await callback.message.delete()
    await callback.answer("❌ Cancelled!")


@Client.on_callback_query(filters.regex(r"^none$"))
async def none_callback(client: Client, callback: CallbackQuery):
    """Handle disabled buttons"""
    await callback.answer("This action is already completed!", show_alert=False)


# ═══════════════════════════════════════════════════════════════════
#  REPLY TO USER COMMAND
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("reply") & filters.user([OWNER_ID] + SUDO_USERS))
async def reply_to_user_cmd(client: Client, message: Message):
    """Reply to a user about their report"""
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Usage:** `/reply <report_id> <message>`\n\n"
            "Example: `/reply RPT12345 We've fixed this issue!`"
        )
    
    report_id = message.command[1].upper()
    reply_text = message.text.split(None, 2)[2]
    
    if report_id not in pending_reports:
        return await message.reply_text(f"❌ Report `{report_id}` not found!")
    
    report = pending_reports[report_id]
    user_id = report.get("user_id")
    
    try:
        await client.send_message(
            user_id,
            f"╔══════════════════════════════════════╗\n"
            f"║   💬 **MESSAGE FROM SUPPORT**        ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"🎫 **Regarding Report:** `{report_id}`\n\n"
            f"📝 **Message:**\n"
            f"{reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 From: {message.from_user.first_name}\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"💕 _Reply with /report if you need more help!_"
        )
        await message.reply_text(f"✅ Message sent to user about `{report_id}`!")
    except Exception as e:
        await message.reply_text(f"❌ Failed to send: {e}")


# ═══════════════════════════════════════════════════════════════════
#  VIEW ALL REPORTS (Owner/Sudo Command)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["reports", "allreports", "pendingbugs"]) & filters.user([OWNER_ID] + SUDO_USERS))
async def view_all_reports_cmd(client: Client, message: Message):
    """View all pending reports"""
    
    # Get from memory first
    pending = [(rid, r) for rid, r in pending_reports.items() if r.get("status") == "pending"]
    investigating = [(rid, r) for rid, r in pending_reports.items() if r.get("status") == "investigating"]
    resolved = [(rid, r) for rid, r in pending_reports.items() if r.get("status") == "resolved"]
    spam = [(rid, r) for rid, r in pending_reports.items() if r.get("status") == "spam"]
    
    if not pending and not investigating:
        return await message.reply_text(
            "╔══════════════════════════════════════╗\n"
            "║      📭 **NO PENDING REPORTS!**      ║\n"
            "╚══════════════════════════════════════╝\n\n"
            "✨ All clear! No bugs reported.\n"
            "🎉 Great job keeping things running smoothly!"
        )
    
    text = "╔══════════════════════════════════════╗\n"
    text += "║       📋 **ALL REPORTS**             ║\n"
    text += "╚══════════════════════════════════════╝\n\n"
    
    if pending:
        text += "**🔴 Pending:**\n"
        for rid, report in pending[:10]:
            priority = report.get("priority", "Medium")
            priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "🟡")
            text += f"• `{rid}` {priority_emoji} - {report.get('first_name', 'Unknown')}\n"
            text += f"  └ {report.get('report_text', '')[:40]}...\n"
        if len(pending) > 10:
            text += f"  _...and {len(pending) - 10} more_\n"
        text += "\n"
    
    if investigating:
        text += "**🔍 Investigating:**\n"
        for rid, report in investigating[:5]:
            text += f"• `{rid}` - {report.get('first_name', 'Unknown')}\n"
        if len(investigating) > 5:
            text += f"  _...and {len(investigating) - 5} more_\n"
        text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "📊 **Statistics:**\n"
    text += f"• 🔴 Pending: {len(pending)}\n"
    text += f"• 🔍 Investigating: {len(investigating)}\n"
    text += f"• ✅ Resolved: {len(resolved)}\n"
    text += f"• 🚫 Spam: {len(spam)}\n"
    text += f"• 📦 Total in memory: {len(pending_reports)}"
    
    await message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════
#  CLEAR OLD REPORTS (Owner Only)
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["clearreports", "cleanupreports"]) & filters.user(OWNER_ID))
async def clear_old_reports_cmd(client: Client, message: Message):
    """Clear resolved/spam reports from memory"""
    
    to_remove = []
    for rid, report in pending_reports.items():
        if report.get("status") in ["resolved", "spam"]:
            to_remove.append(rid)
    
    for rid in to_remove:
        del pending_reports[rid]
    
    await message.reply_text(
        f"🧹 **Cleanup Complete!**\n\n"
        f"• Removed: {len(to_remove)} resolved/spam reports\n"
        f"• Remaining: {len(pending_reports)} reports in memory"
    )


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

@Client.on_message(filters.command(["scangroups", "syncgroups"]) & filters.user([OWNER_ID] + SUDO_USERS))
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
