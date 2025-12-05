# modules/help.py - Help Module with Image URL

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
from pyrogram.errors import MessageNotModified
import config

# 🖼️ HELP IMAGE URL - Change this to your image URL
HELP_IMAGE_URL = "https://files.catbox.moe/ydj43l.jpg"

# Alternative image URLs you can use:
# HELP_IMAGE_URL = "https://i.imgur.com/abc123.jpg"
# HELP_IMAGE_URL = "https://telegra.ph/file/xxxxx.jpg"
# HELP_IMAGE_URL = "https://i.ibb.co/xxxxx/image.jpg"

_loader = None


def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate category buttons"""
    buttons = []
    row = []

    if not _loader:
        # Default buttons if loader not set
        buttons.append([
            InlineKeyboardButton("🎮 Smash", callback_data="help_smash"),
            InlineKeyboardButton("📦 Collection", callback_data="help_collection")
        ])
        buttons.append([
            InlineKeyboardButton("💰 Economy", callback_data="help_economy"),
            InlineKeyboardButton("👤 Profile", callback_data="help_profile")
        ])
        buttons.append([InlineKeyboardButton("❌ Close", callback_data="help_close")])
        return buttons

    for module_name, data in _loader.get_help_data().items():
        emoji = data.get("emoji", "📦")
        name = data.get("name", module_name)

        row.append(
            InlineKeyboardButton(
                f"{emoji} {name}",
                callback_data=f"help_{module_name}"
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Close button
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="help_close")])

    return buttons


def get_module_text(module_name):
    """Build text for module"""
    
    # Default help texts if loader not available
    default_helps = {
        "smash": {
            "emoji": "🎮",
            "name": "Smash Game",
            "description": "Play Smash or Pass with anime waifus!",
            "commands": {
                "smash": "Start a new game",
                "waifu": "Same as smash",
                "sp": "Short command for smash"
            }
        },
        "collection": {
            "emoji": "📦",
            "name": "Collection",
            "description": "Manage your waifu collection",
            "commands": {
                "collection": "View your waifus",
                "col": "Short for collection",
                "waifuinfo": "View waifu details"
            }
        },
        "economy": {
            "emoji": "💰",
            "name": "Economy",
            "description": "Coins and trading system",
            "commands": {
                "balance": "Check your coins",
                "daily": "Claim daily reward",
                "shop": "Visit the shop",
                "gift": "Gift coins or waifus"
            }
        },
        "profile": {
            "emoji": "👤",
            "name": "Profile",
            "description": "Your profile and stats",
            "commands": {
                "profile": "View your profile",
                "stats": "View statistics",
                "leaderboard": "Global rankings"
            }
        }
    }
    
    if _loader:
        data = _loader.get_module_help(module_name)
    else:
        data = default_helps.get(module_name)
    
    if not data:
        return "❌ Module not found!"

    emoji = data.get("emoji", "📦")
    name = data.get("name", module_name)
    description = data.get("description", "No description")
    commands = data.get("commands", {})

    text = f"{emoji} **{name}**\n\n"
    text += f"_{description}_\n\n"

    if commands:
        text += "**📋 Commands:**\n"
        for cmd, desc in commands.items():
            text += f"• `/{cmd}` - {desc}\n"

    return text


def setup(app: Client):
    """Setup help module"""
    
    print("📖 [HELP] Setting up help module...")

    # ══════════════════════════════════════════════════════════════
    #  /help Command - Send Photo with URL
    # ══════════════════════════════════════════════════════════════
    
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_cmd(client: Client, message: Message):
        """Main help command"""
        
        print(f"📖 [HELP] /help from {message.from_user.first_name}")

        caption = """
📖 **Smash & Pass Bot - Help**

Welcome to the Waifu Collection Bot! 🎮

🎯 **Quick Start:**
• Use /smash to play the game
• Win waifus and add them to collection
• Trade with friends!

Select a module below to view commands:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        # Send photo using URL
        try:
            await message.reply_photo(
                photo=HELP_IMAGE_URL,
                caption=caption,
                reply_markup=buttons
            )
            print("✅ [HELP] Sent help with image")
        except Exception as e:
            print(f"⚠️ [HELP] Image failed: {e}, sending text...")
            await message.reply_text(caption, reply_markup=buttons)

    # ══════════════════════════════════════════════════════════════
    #  Back to Main Help
    # ══════════════════════════════════════════════════════════════
    
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main(client: Client, callback: CallbackQuery):
        """Back to main help menu"""

        caption = """
📖 **Smash & Pass Bot - Help**

Select a module below to view commands:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        try:
            # Edit with new image
            await callback.message.edit_media(
                InputMediaPhoto(HELP_IMAGE_URL, caption=caption),
                reply_markup=buttons
            )
        except MessageNotModified:
            pass
        except Exception as e:
            print(f"⚠️ [HELP] Edit error: {e}")
            # Try editing caption only
            try:
                await callback.message.edit_caption(
                    caption=caption,
                    reply_markup=buttons
                )
            except:
                pass

        await callback.answer()

    # ══════════════════════════════════════════════════════════════
    #  Module Help
    # ══════════════════════════════════════════════════════════════
    
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module(client: Client, callback: CallbackQuery):
        """Show module specific help"""

        module_name = callback.data.split("_", 1)[1]

        # Handle close
        if module_name == "close":
            await callback.message.delete()
            return await callback.answer()
        
        # Handle main
        if module_name == "main":
            return  # Handled by help_main

        print(f"📖 [HELP] Module: {module_name}")

        caption = get_module_text(module_name)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])

        try:
            # Edit with same/new image
            await callback.message.edit_media(
                InputMediaPhoto(HELP_IMAGE_URL, caption=caption),
                reply_markup=buttons
            )
        except MessageNotModified:
            pass
        except Exception as e:
            print(f"⚠️ [HELP] Edit error: {e}")
            # Try editing caption only
            try:
                await callback.message.edit_caption(
                    caption=caption,
                    reply_markup=buttons
                )
            except:
                pass

        await callback.answer()

    # ══════════════════════════════════════════════════════════════
    #  Close Help
    # ══════════════════════════════════════════════════════════════
    
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client: Client, callback: CallbackQuery):
        """Close help menu"""
        try:
            await callback.message.delete()
        except:
            pass
        await callback.answer()

    print("✅ [HELP] Help module loaded!")