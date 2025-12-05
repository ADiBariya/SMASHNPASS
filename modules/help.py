from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
import os
import config

# Path to your image
HELP_IMAGE_PATH = "assets/smash.jpg"

_loader = None


def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate category buttons"""
    buttons = []
    row = []

    if not _loader:
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
    data = _loader.get_module_help(module_name)
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

    # ------------------------------------------------------
    #  /help MUST SEND PHOTO
    # ------------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_cmd(_, message: Message):

        caption = (
            "📖 **Smash & Pass Bot - Help**\n\n"
            "Select a module below to view commands:"
        )

        buttons = InlineKeyboardMarkup(get_help_buttons())

        # SEND PHOTO (required for later edit)
        with open(HELP_IMAGE_PATH, "rb") as img:
            await message.reply_photo(
                photo=img,
                caption=caption,
                reply_markup=buttons
            )

    # ------------------------------------------------------
    # Back to Main help
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main(_, callback: CallbackQuery):

        caption = (
            "📖 **Smash & Pass Bot - Help**\n\n"
            "Select a module:"
        )

        buttons = InlineKeyboardMarkup(get_help_buttons())

        with open(HELP_IMAGE_PATH, "rb") as img:
            await callback.message.edit_media(
                InputMediaPhoto(img, caption=caption),
                reply_markup=buttons
            )

        await callback.answer()

    # ------------------------------------------------------
    # Module help
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module(_, callback: CallbackQuery):

        module_name = callback.data.split("_", 1)[1]

        if module_name == "close":
            await callback.message.delete()
            return await callback.answer()

        caption = get_module_text(module_name)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])

        with open(HELP_IMAGE_PATH, "rb") as img:
            await callback.message.edit_media(
                InputMediaPhoto(img, caption=caption),
                reply_markup=buttons
            )

        await callback.answer()

    # ------------------------------------------------------
    # Close
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(_, callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer()
