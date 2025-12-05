from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
import os
import config

# ──────────────────────────────
# DIRECT PATH - BEST & SAFEST METHOD (used by all big bots)
# ──────────────────────────────
HELP_IMAGE_PATH = "assets/smash.jpg"  # Keep this exact path

_loader = None


def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
    """Generate category buttons in 2 columns"""
    buttons = []
    row = []

    if not _loader:
        return [[InlineKeyboardButton("❌ Close", callback_data="help_close")]]

    for module_name, data in _loader.get_help_data().items():
        emoji = data.get("emoji", "📦")
        name = data.get("name", module_name.capitalize())

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

    return InlineKeyboardMarkup(buttons)


def get_module_text(module_name):
    """Build text for specific module"""
    data = _loader.get_module_help(module_name)
    if not data:
        return "❌ Module not found or has no help data."

    emoji = data.get("emoji", "📦")
    name = data.get("name", module_name.capitalize())
    description = data.get("description", "No description available.")
    commands = data.get("commands", {})

    text = f"{emoji} **{name}**\n\n"
    text += f"_{description}_\n\n"

    if commands:
        text += "**📋 Commands:**\n"
        for cmd, desc in commands.items():
            text += f"• `/{cmd}` - {desc}\n"
    else:
        text += "_No commands available for this module._"

    return text


def setup(app: Client):

    # ------------------------------------------------------
    # /help Command - Sends Photo with Buttons
    # ------------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_cmd(_, message: Message):
        caption = (
            "📖 **Smash & Pass Bot - Help Menu**\n\n"
            "Please select a module below to view its commands:"
        )

        buttons = get_help_buttons()

        await message.reply_photo(
            photo=HELP_IMAGE_PATH,        # Direct path → image never disappears
            caption=caption,
            reply_markup=buttons
        )

    # ------------------------------------------------------
    # Back to Main Help Menu
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main(_, callback: CallbackQuery):
        caption = (
            "📖 **Smash & Pass Bot - Help Menu**\n\n"
            "Please select a module below to view its commands:"
        )

        buttons = get_help_buttons()

        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=HELP_IMAGE_PATH,    # Direct path → 100% reliable
                caption=caption
            ),
            reply_markup=buttons
        )
        await callback.answer("🔙 Back to main menu")

    # ------------------------------------------------------
    # Show Specific Module Help
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module(_, callback: CallbackQuery):
        module_name = callback.matches[0].group(1)

        # Close button
        if module_name == "close":
            await callback.message.delete()
            await callback.answer()
            return

        caption = get_module_text(module_name)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_main")],
            [InlineKeyboardButton("❌ Close", callback_data="help_close")]
        ])

        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=HELP_IMAGE_PATH,    # This is the fix - direct path
                caption=caption
            ),
            reply_markup=buttons
        )
        await callback.answer()

    # ------------------------------------------------------
    # Close Help (Delete Message)
    # ------------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(_, callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer()
