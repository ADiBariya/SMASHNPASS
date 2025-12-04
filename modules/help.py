# modules/help.py - Help System Module

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from config import Config

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

# Store reference to loader (set by main.py)
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
    
    # Add close button
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
    
    @app.on_message(filters.command("help", Config.CMD_PREFIX))
    async def help_command(client: Client, message: Message):
        """Handle /help command"""
        text = """
📖 **Smash & Pass Bot - Help**

Welcome to the help menu! Select a category below to learn more about the bot's features.

**🎮 Quick Start:**
1. Use `/smash` to get a random waifu
2. Click **Smash** to try winning her
3. If you win, she joins your collection!

**Select a category:**
"""
        
        buttons = InlineKeyboardMarkup(get_help_buttons())
        
        await message.reply_text(text, reply_markup=buttons)
    
    
    @app.on_message(filters.command("commands", Config.CMD_PREFIX))
    async def commands_list(client: Client, message: Message):
        """List all available commands"""
        if not _loader:
            await message.reply_text("❌ Error loading commands!")
            return
        
        text = "📋 **All Available Commands:**\n\n"
        
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
    
    
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main_callback(client: Client, callback: CallbackQuery):
        """Handle main help callback"""
        text = """
📖 **Smash & Pass Bot - Help**

Welcome to the help menu! Select a category below to learn more about the bot's features.

**🎮 Quick Start:**
1. Use `/smash` to get a random waifu
2. Click **Smash** to try winning her
3. If you win, she joins your collection!

**Select a category:**
"""
        
        buttons = InlineKeyboardMarkup(get_help_buttons())
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()
    
    
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module_callback(client: Client, callback: CallbackQuery):
        """Handle module help callbacks"""
        module_name = callback.data.split("_", 1)[1]
        
        if module_name == "close":
            await callback.message.delete()
            await callback.answer("Help closed!")
            return
        
        if module_name == "main":
            return  # Handled by help_main_callback
        
        text = get_module_help_text(module_name)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])
        
        await callback.message.edit_text(text, reply_markup=buttons)
        await callback.answer()