# modules/leaderboard.py - Leaderboard Module (FIXED)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database import db
import config
import logging

# Setup logger
logger = logging.getLogger(__name__)

__MODULE__ = "Leaderboard"
__HELP__ = """
🏆 **Leaderboard Commands**

• `/leaderboard` - View leaderboard menu
• `/topcollectors` - View top collectors
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
    try:
        # First check if we have name in user_data
        if user_data:
            # Check display_name first (custom name set by user)
            if user_data.get("display_name"):
                return str(user_data["display_name"])[:20]

            # Check first_name
            if user_data.get("first_name"):
                return str(user_data["first_name"])[:20]

            # Check username
            if user_data.get("username"):
                return f"@{user_data['username']}"[:20]

        # If no name found, try to fetch from Telegram
        try:
            user = await client.get_users(user_id)
            if user:
                name = user.first_name or user.username or f"User {user_id}"
                
                # Save name to database for future use
                try:
                    db.users.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "first_name": user.first_name,
                            "username": user.username,
                            "display_name": user.first_name
                        }},
                        upsert=True
                    )
                except Exception as db_error:
                    logger.warning(f"Could not update user in DB: {db_error}")
                
                return str(name)[:20]
        except Exception as e:
            logger.warning(f"Could not fetch user {user_id} from Telegram: {e}")

        return f"User {user_id}"

    except Exception as e:
        logger.error(f"Error in get_user_name for {user_id}: {e}")
        return f"User {user_id}"


def setup(app: Client):
    """Setup leaderboard module with sexy UI"""

    # =========================================
    # /leaderboard, /lb - Main Menu
    # =========================================
    @app.on_message(filters.command(["leaderboard", "lb"], config.COMMAND_PREFIX))
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

        try:
            await message.reply_photo(
                photo="https://i.imgur.com/8K8vH3D.png",  # Working placeholder image
                caption=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Could not send photo: {e}")
            await message.reply_text(
                text=text,
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
            await callback.message.edit_text(
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

        await callback.answer()

    # =========================================
    # Top Collectors - Sexy Waifu Collectors
    # =========================================
    @app.on_callback_query(filters.regex("^lb_collectors$"))
    async def lb_collectors_callback(client: Client, callback: CallbackQuery):
        """Show top waifu collectors with sexy layout"""
        await callback.answer("Loading top collectors...")

        try:
            top_users = db.get_top_collectors(10)
            logger.info(f"Top collectors data: {top_users}")
        except Exception as e:
            logger.error(f"Error fetching top collectors: {e}")
            top_users = []

        text = "📦 **👑 TOP WAIFU COLLECTORS 👑**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No collectors yet! Be the first to collect waifus!*\n\n"
            text += "Use `/smash` to start collecting!"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
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
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

    # =========================================
    # Top Winners - Battle Champions
    # =========================================
    @app.on_callback_query(filters.regex("^lb_winners$"))
    async def lb_winners_callback(client: Client, callback: CallbackQuery):
        """Show top winners with battle-themed layout"""
        await callback.answer("Loading top winners...")

        try:
            top_users = db.get_top_winners(10)
            logger.info(f"Top winners data: {top_users}")
        except Exception as e:
            logger.error(f"Error fetching top winners: {e}")
            top_users = []

        text = "🎯 **🏆 TOP BATTLE CHAMPIONS 🏆**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No winners yet! Start battling to climb the ranks!*\n\n"
            text += "Use `/battle` to start competing!"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
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
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

    # =========================================
    # Richest Players - Coin Masters
    # =========================================
    @app.on_callback_query(filters.regex("^lb_rich$"))
    async def lb_rich_callback(client: Client, callback: CallbackQuery):
        """Show richest players with money-themed layout"""
        await callback.answer("Loading richest players...")

        try:
            top_users = db.get_top_rich(10)
            logger.info(f"Top rich data: {top_users}")
        except Exception as e:
            logger.error(f"Error fetching top rich: {e}")
            top_users = []

        text = "💰 **💎 TOP COIN MASTERS 💎**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No rich players yet! Earn coins to get on this list!*\n\n"
            text += "Use `/daily` to claim free coins!"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                # Get proper name
                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
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
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

    # =========================================
    # Global Stats - Overall Statistics
    # =========================================
    @app.on_callback_query(filters.regex("^lb_global$"))
    async def lb_global_callback(client: Client, callback: CallbackQuery):
        """Show global statistics with sexy layout"""
        await callback.answer("Loading global stats...")

        try:
            stats = db.get_global_stats()
            logger.info(f"Global stats: {stats}")
        except Exception as e:
            logger.error(f"Error fetching global stats: {e}")
            stats = {}

        # Provide defaults if stats is None or empty
        if not stats:
            stats = {
                "total_users": 0,
                "total_waifus_collected": 0,
                "total_smashes": 0,
                "total_passes": 0
            }

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
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

    # =========================================
    # Direct Commands - Quick Access
    # =========================================
    @app.on_message(filters.command("topwins", config.COMMAND_PREFIX))
    async def topwins_command(client: Client, message: Message):
        """Show top winners directly"""
        try:
            top_users = db.get_top_winners(10)
        except Exception as e:
            logger.error(f"Error fetching top winners: {e}")
            await message.reply_text("❌ Error loading leaderboard. Please try again.")
            return

        text = "🎯 **🏆 TOP BATTLE CHAMPIONS 🏆**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No winners yet! Start battling!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
                name = await get_user_name(client, user_id, user_data)
                wins = user_data.get("total_wins", 0)

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
        try:
            top_users = db.get_top_rich(10)
        except Exception as e:
            logger.error(f"Error fetching top rich: {e}")
            await message.reply_text("❌ Error loading leaderboard. Please try again.")
            return

        text = "💰 **💎 TOP COIN MASTERS 💎**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No rich players yet! Earn coins!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
                name = await get_user_name(client, user_id, user_data)
                coins = user_data.get("coins", 0)

                if i == 1:
                    text += f"{medal} **{name}** — {coins:,} coins 💰💎\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {coins:,} coins 💰✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {coins:,} coins 💰🔥\n"
                else:
                    text += f"{medal} **{name}** — {coins:,} coins\n"

        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @app.on_message(filters.command(["topcollectors", "top"], config.COMMAND_PREFIX))
    async def topcollectors_command(client: Client, message: Message):
        """Show top collectors directly"""
        try:
            top_users = db.get_top_collectors(10)
        except Exception as e:
            logger.error(f"Error fetching top collectors: {e}")
            await message.reply_text("❌ Error loading leaderboard. Please try again.")
            return

        text = "📦 **👑 TOP WAIFU COLLECTORS 👑**\n\n"
        medals = ["🥇", "🥈", "🥉"]

        if not top_users:
            text += "*No collectors yet! Be the first!*"
        else:
            for i, user_data in enumerate(top_users, 1):
                medal = medals[i - 1] if i <= 3 else f"**{i}.**"

                user_id = user_data.get("user_id")
                if user_id is None:
                    continue
                    
                name = await get_user_name(client, user_id, user_data)
                count = user_data.get("count", 0)

                if i == 1:
                    text += f"{medal} **{name}** — {count} waifus 💘🔥\n"
                elif i == 2:
                    text += f"{medal} **{name}** — {count} waifus 💖✨\n"
                elif i == 3:
                    text += f"{medal} **{name}** — {count} waifus 💕🌟\n"
                else:
                    text += f"{medal} **{name}** — {count} waifus\n"

        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # =========================================
    # Debug Command (Owner Only)
    # =========================================
    @app.on_message(filters.command("lbdebug", config.COMMAND_PREFIX) & filters.user(config.OWNER_ID))
    async def leaderboard_debug(client: Client, message: Message):
        """Debug leaderboard data - Owner only"""
        try:
            debug_info = db.debug_check_data()
            
            text = "🔧 **Leaderboard Debug Info**\n\n"
            text += f"👥 Total Users: {debug_info.get('users_count', 0)}\n"
            text += f"📦 Total Collections: {debug_info.get('collections_count', 0)}\n"
            text += f"💰 Users with Coins: {debug_info.get('users_with_coins', 0)}\n"
            text += f"🏆 Users with Wins: {debug_info.get('users_with_wins', 0)}\n\n"
            
            sample_user = debug_info.get('sample_user')
            if sample_user:
                text += "**Sample User:**\n"
                text += f"```{str(sample_user)[:500]}```\n\n"
            
            sample_collection = debug_info.get('sample_collection')
            if sample_collection:
                text += "**Sample Collection:**\n"
                text += f"```{str(sample_collection)[:500]}```"
            
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await message.reply_text(f"❌ Debug error: {e}")
