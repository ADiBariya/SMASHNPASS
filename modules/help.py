from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
import config
import logging

# Setup basic logger
logger = logging.getLogger(__name__)

# Help Menu Image (same direct URL pattern as start.py)
HELP_IMAGE = "https://files.catbox.moe/wfekbj.jpg"

# Module info (matches start.py format)
__MODULE__ = "Help"
__HELP__ = """
📖 **Help Commands**
/help - Show full help menu
/commands - List all bot commands
"""

# Loader reference (set by main.py)
_loader = None


def set_loader(loader):
    """Set the module loader reference"""
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate help category buttons (clean 2-column layout)"""
    if not _loader:
        logger.warning("Loader not initialized - minimal buttons")
        return [[InlineKeyboardButton("❌ Close", callback_data="help_close")]]
    
    buttons = []
    row = []
    help_data = _loader.get_help_data()
    
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
    """Get formatted help text for a specific module"""
    if not _loader:
        return "❌ Loader not initialized!"
    
    data = _loader.get_module_help(module_name)
    if not data:
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


# ═══════════════════════════════════════════════════════════════════
#  /help Command
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help", config.COMMAND_PREFIX))
async def help_command(client: Client, message: Message):
    """Handle /help command with image"""
    user = message.from_user

    # Help menu main caption
    text = f"""
📖 **Smash & Pass Bot - Help Menu**

👋 Hello {user.first_name}! Select a category below to learn more about bot commands.

🎮 **Quick Guide:**
• Use /smash to get a random waifu
• Tap **Smash** to try winning her
• Collect rare waifus to climb the leaderboard!

**Choose a category:**
"""
    
    # Generate buttons
    buttons = InlineKeyboardMarkup(get_help_buttons())
    
    # Send with image (exact same pattern as start.py)
    try:
        await message.reply_photo(
            photo=HELP_IMAGE,
            caption=text,
            reply_markup=buttons
        )
        logger.info(f"✅ [HELP] Menu sent to {user.id}")
    except Exception as e:
        print(f"⚠️ [HELP] Image failed: {e}")
        await message.reply_text(text, reply_markup=buttons)


# ═══════════════════════════════════════════════════════════════════
#  /commands List
# ═══════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("commands", config.COMMAND_PREFIX))
async def commands_list(client: Client, message: Message):
    """List all bot commands"""
    if not _loader:
        return await message.reply_text("❌ Error loading commands!")
    
    text = "📋 **All Bot Commands:**\n\n"
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


# ═══════════════════════════════════════════════════════════════════
#  Help Menu Callbacks
# ═══════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^help_main$"))
async def help_main_callback(client: Client, callback: CallbackQuery):
    """Back to main help menu"""
    user = callback.from_user

    text = f"""
📖 **Smash & Pass Bot - Help Menu**

👋 Hello {user.first_name}! Select a category below to learn more.

**Choose a category:**
"""
    
    buttons = InlineKeyboardMarkup(get_help_buttons())
    
    # Exact same edit pattern as start.py
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        print(f"❌ [HELP] Edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^help_(\w+)$"))
async def help_module_callback(client: Client, callback: CallbackQuery):
    """Show help for specific module"""
    module_name = callback.data.split("_", 1)[1]

    # Handle close action
    if module_name == "close":
        await callback.message.delete()
        return await callback.answer("Closed!")

    # Get module help text
    text = get_module_help_text(module_name)
    
    # Back/Close buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
        [InlineKeyboardButton("❌ Close", callback_data="help_close")]
    ])
    
    # Same edit pattern as start.py
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=buttons)
        else:
            await callback.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        print(f"❌ [HELP] Module edit error: {e}")
    
    await callback.answer()


@Client.on_callback_query(filters.regex("^help_close$"))
async def help_close_callback(client: Client, callback: CallbackQuery):
    """Close help menu"""
    await callback.message.delete()
    await callback.answer("Closed!")
