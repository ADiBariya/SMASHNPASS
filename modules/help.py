from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto
)
import os
import config

# Local image path
HELP_IMAGE_PATH = "assets/smash.jpg"   # <-- KEEP YOUR FILE HERE


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

_loader = None


def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
    if not _loader:
        return []

    buttons = []
    row = []
    help_data = _loader.get_help_data()

    for module_name, data in help_data.items():
        emoji = data.get("emoji", "📦")
        name = data.get("name", module_name.title())
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

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="help_close")])
    return buttons


def get_module_help_text(module_name):
    data = _loader.get_module_help(module_name)
    if not data:
        return "❌ Module not found!"

    emoji = data.get("emoji", "📦")
    name = data.get("name", module_name.title())
    description = data.get("description", "No description")
    commands = data.get("commands", {})
    usage = data.get("usage", "")

    text = f"{emoji} **{name}**\n\n_{description}_\n\n"
    if commands:
        text += "**📋 Commands:**\n"
        for cmd, desc in commands.items():
            text += f"• `/{cmd}` - {desc}\n"

    if usage:
        text += f"\n**💡 Usage:**\n{usage}"

    return text


def setup(app: Client):

    # -----------------------------
    # /help command
    # -----------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_command(client, message):

        caption = """
📖 **Smash & Pass Bot - Help**

Choose a category below:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        if os.path.exists(HELP_IMAGE_PATH):
            await message.reply_photo(
                photo=HELP_IMAGE_PATH,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await message.reply_text(caption, reply_markup=buttons)

    # -----------------------------
    # help_main callback
    # -----------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main_callback(client, callback):

        caption = """
📖 **Smash & Pass Bot - Help**

Choose a category:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        if os.path.exists(HELP_IMAGE_PATH):
            with open(HELP_IMAGE_PATH, "rb") as img:
                await callback.message.edit_media(
                    InputMediaPhoto(
                        media=img,
                        caption=caption
                    ),
                    reply_markup=buttons
                )
        else:
            await callback.message.edit_text(caption, reply_markup=buttons)

        await callback.answer()

    # -----------------------------
    # help_{module} callback
    # -----------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def module_help_callback(client, callback):

        module_name = callback.data.split("_", 1)[1]

        if module_name == "close":
            await callback.message.delete()
            return

        text = get_module_help_text(module_name)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])

        if os.path.exists(HELP_IMAGE_PATH):
            with open(HELP_IMAGE_PATH, "rb") as img:
                await callback.message.edit_media(
                    InputMediaPhoto(
                        media=img,
                        caption=text
                    ),
                    reply_markup=buttons
                )
        else:
            await callback.message.edit_text(text, reply_markup=buttons)

        await callback.answer()

    # -----------------------------
    # help_close
    # -----------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client, callback):
        await callback.message.delete()
        await callback.answer("Closed!")
