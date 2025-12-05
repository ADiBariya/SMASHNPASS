# modules/help.py - Help System Module

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
import config

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
        return []

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
    """Get help text for a specific module"""
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
            text += f"• `/{cmd}` - {desc}\n"

    if usage:
        text += f"\n**💡 Usage:**\n{usage}"

    return text


def setup(app: Client):
    """Setup function called by loader"""

    # ---------------------------------------------------------
    #  /help command
    # ---------------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_command(client: Client, message: Message):
        text = """
📖 **Smash & Pass Bot - Help**

Welcome to the help menu! Select a category below to learn more.

🎮 **Quick Start:**
1. Use `/smash` to get a random waifu  
2. Tap **Smash** to try winning  
3. If successful → added to your collection!

**Choose a category:**  
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())
        await message.reply_text(text, reply_markup=buttons)

    # ---------------------------------------------------------
    #  /commands list
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
                    text += f"  • `/{cmd}` - {desc}\n"
                text += "\n"

        await message.reply_text(text)

    # ---------------------------------------------------------
    #  Back to main help menu
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main_callback(client: Client, callback: CallbackQuery):

        text = """
📖 **Smash & Pass Bot - Help**

Welcome to the help menu!

🎮 **Quick Start**
1. Use `/smash`  
2. Click **Smash**  
3. Win → add to collection!

**Choose a category:**
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()

    # ---------------------------------------------------------
    #  Selected module help
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

        await callback.message.edit_media(
    media=InputMediaPhoto(
        "https://i.ibb.co/Mx3WS7Qs/photo-2025-12-05-20-59-39.jpg",
        caption=text
    ),
    reply_markup=buttons
)
        await callback.answer()

    # ---------------------------------------------------------
    #  Close help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client: Client, callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer("Closed!")
