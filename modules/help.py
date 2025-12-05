from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
import config
import logging
import requests
from io import BytesIO

# --------------------------
# Replace this with your actual Catbox image URL
# --------------------------
HELP_IMAGE_URL = "https://files.catbox.moe/wfekbj.jpg"

# Setup module logger for debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Help data for this module
HELP = {
    "name": "Help",
    "emoji": "📖",
    "description": "Help and information commands",
    "commands": {
        "help": "Show help menu",
        "commands": "List all commands"
    }
}

# Loader reference (set by main.py)
_loader = None


def set_loader(loader):
    """Set the module loader reference"""
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate help category buttons"""
    if not _loader:
        logger.warning("Loader not initialized - returning minimal buttons")
        return [[InlineKeyboardButton("❌ Close", callback_data="help_close")]]
    
    buttons = []
    row = []
    help_data = _loader.get_help_data()
    logger.debug(f"Generating buttons for {len(help_data)} modules")
    
    for module_name, data in help_data.items():
        emoji = data.get("emoji", "📦")
        name = data.get("name", module_name.title())
        
        btn = InlineKeyboardButton(
            f"{emoji} {name}",
            callback_data=f"help_{module_name}"
        )
        row.append(btn)
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="help_close")])
    return buttons


def get_module_help_text(module_name: str) -> str:
    """Get help text for a specific module"""
    if not _loader:
        return "❌ Loader not initialized!"
    
    data = _loader.get_module_help(module_name)
    if not data:
        logger.warning(f"Module help not found for: {module_name}")
        return "❌ Module not found!"
    
    emoji = data.get("emoji", "📦")
    name = data.get("name", module_name.title())
    description = data.get("description", "No description")
    commands = data.get("commands", {})
    usage = data.get("usage", "")

    text = f"{emoji} **{name}**\n\n"
    text += f"_{description}_\n\n"

    if commands:
        text += "**📋 Commands:**\n"
        for cmd, desc in commands.items():
            text += f"• /{cmd} - {desc}\n"
    
    if usage:
        text += f"\n**💡 Usage:**\n{usage}"
    
    return text


def fetch_help_image() -> BytesIO | None:
    """Fetch help image from Catbox reliably with redirect handling"""
    try:
        # Mimic browser headers to avoid Catbox blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Fetch image with redirect following and timeout
        response = requests.get(
            HELP_IMAGE_URL, 
            headers=headers, 
            allow_redirects=True, 
            timeout=10
        )
        response.raise_for_status()  # Trigger error for HTTP 4xx/5xx
        
        # Validate content is an image
        if not response.headers.get("Content-Type", "").startswith("image/"):
            logger.error(f"Help image URL returned non-image content: {response.headers.get('Content-Type')}")
            return None
        
        # Return as BytesIO object for Pyrogram
        img_bytes = BytesIO(response.content)
        img_bytes.name = "help_image.jpg"
        return img_bytes
    
    except Exception as e:
        logger.error(f"Failed to fetch help image: {str(e)}", exc_info=True)
        return None


def setup(app: Client):
    """Setup function called by loader"""

    # ---------------------------------------------------------
    # /help command - Sends help image + menu
    # ---------------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_command(client: Client, message: Message):
        caption = (
            "📖 **Smash & Pass Bot - Help**\n\n"
            "Welcome to the help menu! Select a category below to learn more.\n\n"
            "🎮 **Quick Start:**\n"
            "1. Use /smash to get a random waifu\n"
            "2. Tap **Smash** to try winning\n"
            "3. If successful → added to your collection!\n\n"
            "**Choose a category:**"
        )

        buttons = InlineKeyboardMarkup(get_help_buttons())
        logger.debug("Processing /help command - fetching image")
        
        # Fetch image reliably
        img_data = fetch_help_image()
        
        if not img_data:
            logger.error("Failed to load help image - falling back to text")
            await message.reply_text(caption, reply_markup=buttons)
            return

        try:
            # Send image with caption
            await message.reply_photo(
                photo=img_data,
                caption=caption,
                reply_markup=buttons
            )
            logger.debug("Help image sent successfully")
        
        except Exception as e:
            logger.error(f"Failed to send help photo: {str(e)}", exc_info=True)
            await message.reply_text(caption, reply_markup=buttons)

    # ---------------------------------------------------------
    # /commands list
    # ---------------------------------------------------------
    @app.on_message(filters.command("commands", config.COMMAND_PREFIX))
    async def commands_list(client: Client, message: Message):
        if not _loader:
            return await message.reply_text("❌ Error loading commands!")
        
        text = "📋 **All Commands:**\n\n"
        for module_name, data in _loader.get_help_data().items():
            emoji = data.get("emoji", "📦")
            name = data.get("name", module_name.title())
            commands = data.get("commands", {})
            
            if commands:
                text += f"{emoji} **{name}:**\n"
                for cmd, desc in commands.items():
                    text += f" • /{cmd} - {desc}\n"
                text += "\n"
        
        await message.reply_text(text)

    # ---------------------------------------------------------
    # Back to main help menu
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main_callback(client: Client, callback: CallbackQuery):
        caption = (
            "📖 **Smash & Pass Bot - Help**\n\n"
            "Welcome to the help menu!\n\n"
            "🎮 **Quick Start**\n"
            "1. Use /smash\n"
            "2. Click **Smash**\n"
            "3. Win → add to collection!\n\n"
            "**Choose a category:**"
        )

        buttons = InlineKeyboardMarkup(get_help_buttons())
        
        try:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=buttons
            )
            logger.debug("Help main menu caption updated")
        except Exception as e:
            logger.error(f"Failed to update main help caption: {str(e)}", exc_info=True)
        
        await callback.answer()

    # ---------------------------------------------------------
    # Selected module help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module_callback(client: Client, callback: CallbackQuery):
        module_name = callback.data.split("_", 1)[1]

        if module_name == "close":
            await callback.message.delete()
            return await callback.answer("Closed!")

        text = get_module_help_text(module_name)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])
        
        try:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=buttons
            )
            logger.debug(f"Module help updated for: {module_name}")
        except Exception as e:
            logger.error(f"Failed to update module help: {str(e)}", exc_info=True)
            await callback.message.edit_text(text, reply_markup=buttons)
        
        await callback.answer()

    # ---------------------------------------------------------
    # Close help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client: Client, callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer("Closed!")
