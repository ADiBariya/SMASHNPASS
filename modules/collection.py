# modules/collection.py - Collection System Module

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from database import db
from helpers import get_waifu_manager, Utils
import config

# Help data for this module
__MODULE__ = "Collection"
__HELP__ = """
📦 **Collection Commands**

• `/collection` - View your waifu collection
• `/mycollection` - Alias for collection
• `/col` - Short alias for collection
• `/waifu <name>` - View specific waifu details
• `/gift @user <waifu_id>` - Gift a waifu to someone (reply to their message)

**Tips:**
- Use pagination buttons to navigate through your collection
- Filter by rarity to find specific waifus
- Check waifu details before gifting
"""

# Items per page
ITEMS_PER_PAGE = 5


def setup(app: Client):
    """Setup function called by loader"""

    @app.on_message(filters.command(["collection", "mycollection", "col"], config.COMMAND_PREFIX))
    async def collection_command(client: Client, message: Message):
        """View user collection"""
        user = message.from_user
        await show_collection(message, user.id, page=1)

    @app.on_callback_query(filters.regex("^view_collection$"))
    async def view_collection_callback(client: Client, callback: CallbackQuery):
        """Handle view collection callback"""
        user = callback.from_user
        await show_collection_callback(callback, user.id, page=1)

    @app.on_callback_query(filters.regex(r"^col_page_(\d+)$"))
    async def collection_page_callback(client: Client, callback: CallbackQuery):
        """Handle collection pagination"""
        page = int(callback.data.split("_")[2])
        user = callback.from_user
        await show_collection_callback(callback, user.id, page)

    async def show_collection(message: Message, user_id: int, page: int = 1):
        """Show user collection as message"""
        wm = get_waifu_manager()

        # Get user data to check collection
        user_data = await db.get_user(user_id)
        
        if not user_data or 'collection' not in user_data:
            collection = []
            total = 0
        else:
            collection = user_data.get('collection', [])
            total = len(collection)

        if total == 0:
            text = """
📦 **Your Collection**

Your collection is empty!

Use /smash to start collecting waifus!
"""
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")]
            ])
            await message.reply_text(text, reply_markup=buttons)
            return

        # Calculate pagination
        total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total)
        
        # Get waifus for current page
        page_waifus = collection[start_idx:end_idx]

        text = f"📦 **Your Collection** ({total} waifus)\n"
        text += f"Page {page}/{total_pages}\n\n"

        for i, waifu in enumerate(page_waifus, 1):
            # Handle both possible field naming conventions
            waifu_name = waifu.get('name') or waifu.get('waifu_name', 'Unknown')
            waifu_anime = waifu.get('anime') or waifu.get('waifu_anime', 'Unknown')
            waifu_rarity = waifu.get('rarity') or waifu.get('waifu_rarity', 'common')
            waifu_power = waifu.get('power') or waifu.get('waifu_power', 0)
            
            rarity_emoji = wm.get_rarity_emoji(waifu_rarity)
            text += f"{rarity_emoji} **{waifu_name}**\n"
            text += f"   └ {waifu_anime} | ⚔️ {waifu_power}\n"

        # Create pagination buttons
        buttons = []
        nav_row = []

        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_page_{page-1}"))

        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))

        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_page_{page+1}"))

        buttons.append(nav_row)

        # Add filter buttons
        buttons.append([
            InlineKeyboardButton("🟡 Legendary", callback_data="col_filter_legendary"),
            InlineKeyboardButton("🟣 Epic", callback_data="col_filter_epic")
        ])
        buttons.append([
            InlineKeyboardButton("🔵 Rare", callback_data="col_filter_rare"),
            InlineKeyboardButton("⚪ Common", callback_data="col_filter_common")
        ])
        buttons.append([
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
            InlineKeyboardButton("🔙 Back", callback_data="start_back")
        ])

        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    async def show_collection_callback(callback: CallbackQuery, user_id: int, page: int = 1):
        """Show user collection as callback edit"""
        wm = get_waifu_manager()

        # Get user data to check collection
        user_data = await db.get_user(user_id)
        
        if not user_data or 'collection' not in user_data:
            collection = []
            total = 0
        else:
            collection = user_data.get('collection', [])
            total = len(collection)

        if total == 0:
            text = """
📦 **Your Collection**

Your collection is empty! 😢

Use /smash to start collecting waifus!
"""
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Play Now", callback_data="play_smash")],
                [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
            ])
            await callback.message.edit_text(text, reply_markup=buttons)
            await callback.answer()
            return

        # Calculate pagination
        total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total)
        
        # Get waifus for current page
        page_waifus = collection[start_idx:end_idx]

        text = f"📦 **Your Collection** ({total} waifus)\n"
        text += f"Page {page}/{total_pages}\n\n"

        for i, waifu in enumerate(page_waifus, 1):
            # Handle both possible field naming conventions
            waifu_name = waifu.get('name') or waifu.get('waifu_name', 'Unknown')
            waifu_anime = waifu.get('anime') or waifu.get('waifu_anime', 'Unknown')
            waifu_rarity = waifu.get('rarity') or waifu.get('waifu_rarity', 'common')
            waifu_power = waifu.get('power') or waifu.get('waifu_power', 0)
            
            rarity_emoji = wm.get_rarity_emoji(waifu_rarity)
            text += f"{rarity_emoji} **{waifu_name}**\n"
            text += f"   └ {waifu_anime} | ⚔️ {waifu_power}\n"

        # Create pagination buttons
        buttons = []
        nav_row = []

        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"col_page_{page-1}"))

        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col_info"))

        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"col_page_{page+1}"))

        buttons.append(nav_row)

        buttons.append([
            InlineKeyboardButton("🟡 Legendary", callback_data="col_filter_legendary"),
            InlineKeyboardButton("🟣 Epic", callback_data="col_filter_epic")
        ])
        buttons.append([
            InlineKeyboardButton("🎮 Play", callback_data="play_smash"),
            InlineKeyboardButton("🔙 Back", callback_data="start_back")
        ])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        await callback.answer()

    @app.on_callback_query(filters.regex(r"^col_filter_(\w+)$"))
    async def collection_filter_callback(client: Client, callback: CallbackQuery):
        """Handle collection rarity filter"""
        rarity = callback.data.split("_")[2]
        user = callback.from_user
        wm = get_waifu_manager()

        # Get user's collection
        user_data = await db.get_user(user.id)
        if not user_data or 'collection' not in user_data:
            await callback.answer("Your collection is empty!", show_alert=True)
            return

        collection = user_data.get('collection', [])
        
        # Filter by rarity
        filtered_waifus = []
        for waifu in collection:
            waifu_rarity = waifu.get('rarity') or waifu.get('waifu_rarity', 'common')
            if waifu_rarity.lower() == rarity.lower():
                filtered_waifus.append(waifu)

        if not filtered_waifus:
            await callback.answer(f"No {rarity} waifus in your collection!", show_alert=True)
            return

        rarity_emoji = wm.get_rarity_emoji(rarity)

        text = f"{rarity_emoji} **Your {rarity.title()} Waifus** ({len(filtered_waifus)})\n\n"

        for waifu in filtered_waifus[:10]:  # Show max 10
            waifu_name = waifu.get('name') or waifu.get('waifu_name', 'Unknown')
            waifu_anime = waifu.get('anime') or waifu.get('waifu_anime', 'Unknown')
            text += f"• **{waifu_name}** - {waifu_anime}\n"

        if len(filtered_waifus) > 10:
            text += f"\n_...and {len(filtered_waifus) - 10} more_"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Collection", callback_data="view_collection")]
        ])

        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()

    @app.on_callback_query(filters.regex("^col_info$"))
    async def collection_info_callback(client: Client, callback: CallbackQuery):
        """Handle collection info click (page number)"""
        await callback.answer("Use arrows to navigate pages!")

    @app.on_message(filters.command(["waifu", "waifuinfo"], config.COMMAND_PREFIX))
    async def waifu_info_command(client: Client, message: Message):
        """View specific waifu info"""
        wm = get_waifu_manager()
        user = message.from_user

        # Get waifu name from command
        if len(message.command) < 2:
            await message.reply_text(
                "❌ **Usage:** `/waifu <name>`\n\n"
                "Example: `/waifu Hinata`"
            )
            return

        waifu_name = " ".join(message.command[1:])

        # Search in all waifus
        waifu = wm.get_waifu_by_name(waifu_name)

        if not waifu:
            # Try partial search
            results = wm.search_waifus(waifu_name)
            if results:
                text = f"🔍 **Search Results for '{waifu_name}':**\n\n"
                for w in results[:5]:
                    rarity_emoji = wm.get_rarity_emoji(w.get("rarity", "common"))
                    text += f"{rarity_emoji} {w.get('name')} - {w.get('anime')}\n"
                await message.reply_text(text)
            else:
                await message.reply_text(f"❌ Waifu '{waifu_name}' not found!")
            return

        rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))

        # Check if user owns this waifu
        user_data = await db.get_user(user.id)
        owned = False
        
        if user_data and 'collection' in user_data:
            for collected_waifu in user_data['collection']:
                collected_id = collected_waifu.get('id') or collected_waifu.get('waifu_id')
                if collected_id == waifu.get("id"):
                    owned = True
                    break
        
        owned_text = "✅ You own this waifu!" if owned else "❌ Not in your collection"

        text = f"""
{rarity_emoji} **{waifu.get('name')}**

📺 **Anime:** {waifu.get('anime')}
💎 **Rarity:** {waifu.get('rarity', 'common').title()}
⚔️ **Power:** {waifu.get('power', 0)}
🆔 **ID:** {waifu.get('id')}

{owned_text}
"""

        image_url = waifu.get("image")

        if image_url:
            try:
                await message.reply_photo(photo=image_url, caption=text)
            except Exception:
                await message.reply_text(text)
        else:
            await message.reply_text(text)

    @app.on_message(filters.command(["gift", "give"], config.COMMAND_PREFIX))
    async def gift_waifu_command(client: Client, message: Message):
        """Gift a waifu to another user"""
        user = message.from_user

        # Check if replying to someone
        if not message.reply_to_message:
            await message.reply_text(
                "❌ **Usage:** Reply to someone's message with:\n"
                "`/gift <waifu_id>`\n\n"
                "Example: Reply to a user and type `/gift 5`"
            )
            return

        if len(message.command) < 2:
            await message.reply_text("❌ Please specify the waifu ID!\n`/gift <waifu_id>`")
            return

        try:
            waifu_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid waifu ID!")
            return

        target_user = message.reply_to_message.from_user

        if target_user.id == user.id:
            await message.reply_text("❌ You can't gift to yourself!")
            return

        if target_user.is_bot:
            await message.reply_text("❌ You can't gift to a bot!")
            return

        # Get user's collection
        user_data = await db.get_user(user.id)
        
        if not user_data or 'collection' not in user_data:
            await message.reply_text("❌ Your collection is empty!")
            return

        # Find the waifu in collection
        collection = user_data.get('collection', [])
        waifu_to_gift = None
        waifu_index = -1
        
        for idx, waifu in enumerate(collection):
            collected_id = waifu.get('id') or waifu.get('waifu_id')
            if collected_id == waifu_id:
                waifu_to_gift = waifu
                waifu_index = idx
                break

        if not waifu_to_gift:
            await message.reply_text("❌ You don't own this waifu!")
            return

        # Ensure target user exists in db
        await db.get_or_create_user(target_user.id, target_user.username, target_user.first_name)

        # Remove from sender's collection
        collection.pop(waifu_index)
        await db.users.update_one(
            {"user_id": user.id},
            {"$set": {"collection": collection}}
        )

        # Add to receiver's collection
        await db.users.update_one(
            {"user_id": target_user.id},
            {"$push": {"collection": waifu_to_gift}}
        )

        waifu_name = waifu_to_gift.get('name') or waifu_to_gift.get('waifu_name', 'Unknown')
        
        await message.reply_text(
            f"🎁 **Gift Successful!**\n\n"
            f"You gifted **{waifu_name}** to "
            f"{Utils.mention_user(target_user.id, target_user.first_name)}!"
        )
