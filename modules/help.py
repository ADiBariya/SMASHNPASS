from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
import os
import config

# Path to your local image
HELP_IMAGE_PATH = "assets/smash.jpg"

# Loader reference
_loader = None


def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate category buttons"""
    if not _loader:
        return []

    buttons = []
    row = []

    for module_name, data in _loader.get_help_data().items():
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


def get_module_text(module_name):
    """Generate help text for a module"""
    data = _loader.get_module_help(module_name)
    if not data:
        return "❌ Module not found!"

    emoji = data.get("emoji", "📦")
    name = data.get("name")
    description = data.get("description", "No description")

    text = f"{emoji} **{name}**\n\n"
    text += f"_{description}_\n\n"

    cmds = data.get("commands", {})
    if cmds:
        text += "**📋 Commands:**\n"
        for cmd, desc in cmds.items():
            text += f"• `/{cmd}` - {desc}\n"

    return text


def setup(app: Client):
    """Setup help system"""

    # ---------------------------------------------------------
    # /help = MUST SEND PHOTO FIRST
    # ---------------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_cmd(client: Client, message: Message):

        caption = """
📖 **Smash & Pass Bot - Help**

Choose a category below:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        # Send photo → allows photo edits later
        with open(HELP_IMAGE_PATH, "rb") as img:
            await message.reply_photo(
                photo=img,
                caption=caption,
                reply_markup=buttons
            )

    # ---------------------------------------------------------
    # Main help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main(client: Client, callback: CallbackQuery):

        caption = """
📖 **Smash & Pass Bot - Help**

Select a module:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        with open(HELP_IMAGE_PATH, "rb") as img:
            await callback.message.edit_media(
                InputMediaPhoto(media=img, caption=caption),
                reply_markup=buttons
            )

        await callback.answer()

    # ---------------------------------------------------------
    # Module help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module(client: Client, callback: CallbackQuery):

        module_name = callback.data.split("_", 1)[1]

        if module_name == "close":
            await callback.message.delete()
            return await callback.answer("Closed!")

        caption = get_module_text(module_name)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])

        with open(HELP_IMAGE_PATH, "rb") as img:
            await callback.message.edit_media(
                InputMediaPhoto(media=img, caption=caption),
                reply_markup=buttons
            )

        await callback.answer()

    # ---------------------------------------------------------
    # Close help
    # ---------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client: Client, callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer("Closed!")
