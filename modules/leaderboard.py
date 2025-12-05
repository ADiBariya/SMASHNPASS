# # modules/leaderboard.py - Leaderboard Module

# from pyrogram import Client, filters
# from pyrogram.types import (
#     Message,
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery
# )
# from pyrogram.enums import ParseMode
# from database import db
# from helpers import Utils
# import config

# # Help data for this module
# HELP = {
#     "name": "Leaderboard",
#     "emoji": "🏆",
#     "description": "View top players and rankings",
#     "commands": {
#         "leaderboard": "View leaderboard menu",
#         "top": "View top collectors",
#         "topwins": "View top winners",
#         "toprich": "View richest players"
#     }
# }


# async def get_user_name(client: Client, user_id: int, user_data: dict = None) -> str:
#     """Get user's display name - fetch from Telegram if not in database"""
    
#     # First check if we have name in user_data
#     if user_data:
#         # Check display_name first (custom name set by user)
#         if user_data.get("display_name"):
#             return user_data["display_name"]
        
#         # Check first_name
#         if user_data.get("first_name"):
#             return user_data["first_name"]
        
#         # Check username
#         if user_data.get("username"):
#             return user_data["username"]
    
#     # If no name found, try to fetch from Telegram
#     try:
#         user = await client.get_users(user_id)
#         name = user.first_name or user.username or f"User {user_id}"
        
#         # Save name to database for future use
#         db.users.update_one(
#             {"user_id": user_id},
#             {"$set": {"first_name": user.first_name, "username": user.username}},
#             upsert=True
#         )
        
#         return name
#     except Exception:
#         return f"User {user_id}"


# def setup(app: Client):
#     """Setup leaderboard module"""

#     # ----------------------------------------
#     # /leaderboard , /lb , /top
#     # ----------------------------------------
#     @app.on_message(filters.command(["leaderboard", "lb", "top"], config.COMMAND_PREFIX))
#     async def leaderboard_command(client: Client, message: Message):

#         text = """
# 🏆 **Leaderboard**

# Select a category to view:
# """

#         buttons = InlineKeyboardMarkup([
#             [
#                 InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
#                 InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
#             ],
#             [
#                 InlineKeyboardButton("💰 Richest", callback_data="lb_rich"),
#                 InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
#             ]
#         ])

#         await message.reply_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

#     # ----------------------------------------
#     # Back to main
#     # ----------------------------------------
#     @app.on_callback_query(filters.regex("^leaderboard_main$"))
#     async def leaderboard_main_callback(client: Client, callback: CallbackQuery):

#         text = """
# 🏆 **Leaderboard**

# Select a category to view:
# """

#         buttons = InlineKeyboardMarkup([
#             [
#                 InlineKeyboardButton("📦 Top Collectors", callback_data="lb_collectors"),
#                 InlineKeyboardButton("🎯 Top Winners", callback_data="lb_winners")
#             ],
#             [
#                 InlineKeyboardButton("💰 Richest", callback_data="lb_rich"),
#                 InlineKeyboardButton("📊 Global Stats", callback_data="lb_global")
#             ]
#         ])

#         await callback.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)
#         await callback.answer()

#     # ----------------------------------------
#     # Top Collectors
#     # ----------------------------------------
#     @app.on_callback_query(filters.regex("^lb_collectors$"))
#     async def lb_collectors_callback(client: Client, callback: CallbackQuery):

#         await callback.answer("Loading...", show_alert=False)
        
#         top_users = db.get_top_collectors(10)

#         text = "📦 **Top Collectors**\n\n"
#         medals = ["🥇", "🥈", "🥉"]

#         for i, user_data in enumerate(top_users, 1):
#             medal = medals[i - 1] if i <= 3 else f"**{i}.**"
            
#             # Get proper name
#             user_id = user_data.get("user_id")
#             name = await get_user_name(client, user_id, user_data)
#             count = user_data.get("count", 0)

#             text += f"{medal} {name} — {count} waifus\n"

#         if not top_users:
#             text += "_No data yet!_"

#         buttons = InlineKeyboardMarkup([
#             [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
#         ])

#         await callback.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

#     # ----------------------------------------
#     # Top Winners
#     # ----------------------------------------
#     @app.on_callback_query(filters.regex("^lb_winners$"))
#     async def lb_winners_callback(client: Client, callback: CallbackQuery):

#         await callback.answer("Loading...", show_alert=False)
        
#         top_users = db.get_top_winners(10)

#         text = "🎯 **Top Winners**\n\n"
#         medals = ["🥇", "🥈", "🥉"]

#         for i, user_data in enumerate(top_users, 1):
#             medal = medals[i - 1] if i <= 3 else f"**{i}.**"
            
#             # Get proper name
#             user_id = user_data.get("user_id")
#             name = await get_user_name(client, user_id, user_data)
#             wins = user_data.get("total_wins", 0)

#             text += f"{medal} {name} — {wins} wins\n"

#         if not top_users:
#             text += "_No data yet!_"

#         buttons = InlineKeyboardMarkup([
#             [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
#         ])

#         await callback.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

#     # ----------------------------------------
#     # Richest Players
#     # ----------------------------------------
#     @app.on_callback_query(filters.regex("^lb_rich$"))
#     async def lb_rich_callback(client: Client, callback: CallbackQuery):

#         await callback.answer("Loading...", show_alert=False)
        
#         top_users = db.get_top_rich(10)

#         text = "💰 **Richest Players**\n\n"
#         medals = ["🥇", "🥈", "🥉"]

#         for i, user_data in enumerate(top_users, 1):
#             medal = medals[i - 1] if i <= 3 else f"**{i}.**"
            
#             # Get proper name
#             user_id = user_data.get("user_id")
#             name = await get_user_name(client, user_id, user_data)
#             coins = user_data.get("coins", 0)

#             text += f"{medal} {name} — {coins:,} coins\n"

#         if not top_users:
#             text += "_No data yet!_"

#         buttons = InlineKeyboardMarkup([
#             [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
#         ])

#         await callback.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

#     # ----------------------------------------
#     # Global Stats
#     # ----------------------------------------
#     @app.on_callback_query(filters.regex("^lb_global$"))
#     async def lb_global_callback(client: Client, callback: CallbackQuery):

#         stats = db.get_global_stats()

#         text = f"""
# 📊 **Global Statistics**

# 👥 **Total Users:** {stats.get('total_users', 0):,}
# 📦 **Waifus Collected:** {stats.get('total_waifus_collected', 0):,}
# 💥 **Total Smashes:** {stats.get('total_smashes', 0):,}
# 👋 **Total Passes:** {stats.get('total_passes', 0):,}
# """

#         buttons = InlineKeyboardMarkup([
#             [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
#         ])

#         await callback.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)
#         await callback.answer()

#     # ----------------------------------------
#     # Direct Commands
#     # ----------------------------------------
#     @app.on_message(filters.command("topwins", config.COMMAND_PREFIX))
#     async def topwins_command(client: Client, message: Message):

#         top_users = db.get_top_winners(10)

#         text = "🎯 **Top Winners**\n\n"
#         medals = ["🥇", "🥈", "🥉"]

#         for i, user_data in enumerate(top_users, 1):
#             medal = medals[i - 1] if i <= 3 else f"**{i}.**"
            
#             # Get proper name
#             user_id = user_data.get("user_id")
#             name = await get_user_name(client, user_id, user_data)
#             wins = user_data.get("total_wins", 0)

#             text += f"{medal} {name} — {wins} wins\n"

#         if not top_users:
#             text += "_No data yet!_"

#         await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

#     @app.on_message(filters.command("toprich", config.COMMAND_PREFIX))
#     async def toprich_command(client: Client, message: Message):

#         top_users = db.get_top_rich(10)

#         text = "💰 **Richest Players**\n\n"
#         medals = ["🥇", "🥈", "🥉"]

#         for i, user_data in enumerate(top_users, 1):
#             medal = medals[i - 1] if i <= 3 else f"**{i}.**"
            
#             # Get proper name
#             user_id = user_data.get("user_id")
#             name = await get_user_name(client, user_id, user_data)
#             coins = user_data.get("coins", 0)

#             text += f"{medal} {name} — {coins:,} coins\n"

#         if not top_users:
#             text += "_No data yet!_"

#         await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
