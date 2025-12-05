from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database import db
from helpers import Utils
import config

__MODULE__ = "Leaderboard"
__HELP__ = """
🏆 **Leaderboard Commands**

• `/leaderboard` - View leaderboard menu
• `/top` - View top collectors
• `/topwins` - View top winners
• `/toprich` - View richest players

💎 **Features:**
- Beautiful medal system
- Interactive buttons
- Detailed statistics
- Global rankings
"""

async def get_user_name(client: Client, user_id: int, user_data: dict = None) -> str:
    """Get user's display name - fetch from Telegram if not in database"""
    # First check if we have name in user_data
    if user_data:
        # Check display_name first (custom name set by user)
        if user_data.get("display_name"):
            return user_data["display_name"]

        # Check first_name
        if user_data.get("first_name"):
            return user_data["first_name"]

        # Check username
        if user_data.get("username"):
            return user_data["username"]

    # If no name found, try to fetch from Telegram
    try:
        user = await client.get_users(user_id)
        name = user.first_name or user.username or f"User {user_id}"

        # Save name to database for future use
        db.users.update_one(
            {"user_id": user_id},
            {"$set": {"first_name": user.first_name, "username": user.username}},
            upsert=True
        )

        return name
    except Exception:
        return f"User {user_id}"

def setup(app: Client):
    """Setup leaderboard module with sexy UI"""

    # =========================================
    # /leaderboard, /lb, /top - Main Menu
    # =========================================
    @app.on_message(filters.command(["leaderboard", "lb", "top"], config.COMMAND_PREFIX))
    async def leaderboard_command(client: Client, message: Message):
        """Show sexy leaderboard main menu"""
        text = """
🏆 **🌟 LEADERBOARD 🌟**

*Who's on top? Check the rankings!*

💖 *Compete to be the best!*
"""

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
                InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
            ],
            [
                InlineKeyboardButton("💰 Richest Players", callback_data="lb_rich"),
                InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
            ]
        ])

        await message.reply_photo(
            photo="https://i.imgur.com/JQJQJQJ.png",  # Replace with your sexy leaderboard image
            caption=text,
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN
        )

    # =========================================
    # Back to main menu
    # =========================================
    @app.on_callback_query(filters.regex("^leaderboard_main$"))
    async def leaderboard_main_callback(client: Client, callback: CallbackQuery):
        """Return to main leaderboard menu"""
        text = """
🏆 **🌟 LEADERBOARD 🌟**

*Who's on top? Check the rankings!*

💖 *Compete to be the best!*
"""

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
                InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
            ],
            [
                InlineKeyboardButton("💰 Richest Players", callback_data="lb_rich"),
                InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
            ]
        ])

        try:
            await callback.message.edit_media(
                input_media=callback.message.photo.file_id,
                reply_markup=buttons
            )
            await callback.message.edit_caption(
                caption=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        await callback.answer()

    # =========================================
    # Top Collectors - Sexy Waifu Collectors
    # =========================================
    @app.on_callback_query(filters.regex("^lb_collectors$"))
    async def lb_collectors_callback(client: Client, callback: CallbackQuery):
        """Show top waifu collectors with sexy layout"""
        await callback.answer("Loading top collectors...", show_alert=True)

        top_users = db.get_top_collectors(10)

        text = "📦 **👑 TOP WAIFU COLLECTORS 👑**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No collectors yet! Be the first!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                count = user_data.get("count", 0)

                # Add sexy emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {count} waifus 💘🔥\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {count} waifus 💖✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {count} waifus 💕🌟\n"
                else:
                    text += f"{medal} **{name}** — {count} waifus\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="leaderboard_main")]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.edit_text(
                text=f"Error loading leaderboard: {e}",
                reply_markup=buttons
            )
        await callback.answer()

    # =========================================
    # Top Winners - Battle Champions
    # =========================================
    @app.on_callback_query(filters.regex("^lb_winners$"))
    async def lb_winners_callback(client: Client, callback: CallbackQuery):
        """Show top winners with battle-themed layout"""
        await callback.answer("Loading top winners...", show_alert=True)

        top_users = db.get_top_winners(10)

        text = "🎯 **🏆 TOP BATTLE CHAMPIONS 🏆**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No winners yet! Start battling!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                wins = user_data.get("total_wins", 0)

                # Add battle emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {wins} wins ⚔️💥\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {wins} wins ⚔️🔥\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {wins} wins ⚔️✨\n"
                else:
                    text += f"{medal} **{name}** — {wins} wins\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="leaderboard_main")]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.edit_text(
                text=f"Error loading leaderboard: {e}",
                reply_markup=buttons
            )
        await callback.answer()

    # =========================================
    # Richest Players - Coin Masters
    # =========================================
    @app.on_callback_query(filters.regex("^lb_rich$"))
    async def lb_rich_callback(client: Client, callback: CallbackQuery):
        """Show richest players with money-themed layout"""
        await callback.answer("Loading richest players...", show_alert=True)

        top_users = db.get_top_rich(10)

        text = "💰 **💎 TOP COIN MASTERS 💎**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No rich players yet! Earn coins!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                coins = user_data.get("coins", 0)

                # Add money emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {coins:,} coins 💰💎\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {coins:,} coins 💰✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {coins:,} coins 💰🔥\n"
                else:
                    text += f"{medal} **{name}** — {coins:,} coins\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="leaderboard_main")]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.edit_text(
                text=f"Error loading leaderboard: {e}",
                reply_markup=buttons
            )
        await callback.answer()

    # =========================================
    # Global Stats - Overall Statistics
    # =========================================
    @app.on_callback_query(filters.regex("^lb_global$"))
    async def lb_global_callback(client: Client, callback: CallbackQuery):
        """Show global statistics with sexy layout"""
        await callback.answer("Loading global stats...", show_alert=True)

        stats = db.get_global_stats()

        text = f"""
📊 **🌍 GLOBAL STATISTICS 🌍**

👥 **Total Users:** {stats.get('total_users', 0):,}
📦 **Waifus Collected:** {stats.get('total_waifus_collected', 0):,}
💥 **Total Smashes:** {stats.get('total_smashes', 0):,}
👋 **Total Passes:** {stats.get('total_passes', 0):,}

*Keep playing to improve these numbers!* 💖
"""

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="leaderboard_main")]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.edit_text(
                text=f"Error loading stats: {e}",
                reply_markup=buttons
            )
        await callback.answer()

    # =========================================
    # Direct Commands - Quick Access
    # =========================================
    @app.on_message(filters.command("topwins", config.COMMAND_PREFIX))
    async def topwins_command(client: Client, message: Message):
        """Show top winners directly"""
        top_users = db.get_top_winners(10)

        text = "🎯 **🏆 TOP BATTLE CHAMPIONS 🏆**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No winners yet! Start battling!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                wins = user_data.get("total_wins", 0)

                # Add battle emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {wins} wins ⚔️💥\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {wins} wins ⚔️🔥\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {wins} wins ⚔️✨\n"
                else:
                    text += f"{medal} **{name}** — {wins} wins\n"

        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @app.on_message(filters.command("toprich", config.COMMAND_PREFIX))
    async def toprich_command(client: Client, message: Message):
        """Show richest players directly"""
        top_users = db.get_top_rich(10)

        text = "💰 **💎 TOP COIN MASTERS 💎**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No rich players yet! Earn coins!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                coins = user_data.get("coins", 0)

                # Add money emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {coins:,} coins 💰💎\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {coins:,} coins 💰✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {coins:,} coins 💰🔥\n"
                else:
                    text += f"{medal} **{name}** — {coins:,} coins\n"

        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @app.on_message(filters.command("top", config.COMMAND_PREFIX))
    async def top_command(client: Client, message: Message):
        """Show top collectors directly"""
        top_users = db.get_top_collectors(10)

        text = "📦 **👑 TOP WAIFU COLLECTORS 👑**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No collectors yet! Be the first!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                name = await get_user_name(client, user_id, user_data)
                count = user_data.get("count", 0)

                # Add sexy emojis based on position
                if i == 1:
                    text += f"{medal} **{name}** — {count} waifus 💘🔥\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {count} waifus 💖✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {count} waifus 💕🌟\n"
                else:
                    text += f"{medal} **{name}** — {count} waifus\n"

        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
