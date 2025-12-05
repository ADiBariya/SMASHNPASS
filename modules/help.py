from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaPhoto
)
import os
import config

HELP_IMAGE_PATH = "assets/help.jpg"   # <--- Your image path

_loader = None

def set_loader(loader):
    global _loader
    _loader = loader


def get_help_buttons():
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
    data = _loader.get_module_help(module_name)
    if not data:
        return "❌ Module not found!"

    text = f"{data.get('emoji','📦')} **{data.get('name')}**\n\n"
    text += f"_{data.get('description','No description')}_\n\n"

    cmds = data.get("commands", {})
    for cmd, desc in cmds.items():
        text += f"• `/{cmd}` - {desc}\n"

    return text


def setup(app: Client):

    # ----------------------------------------------------
    # FIRST HELP MESSAGE (MUST BE PHOTO)
    # ----------------------------------------------------
    @app.on_message(filters.command("help", config.COMMAND_PREFIX))
    async def help_cmd(client, message):

        caption = """
📖 **Smash & Pass - Help**

Select a category below:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        with open(HELP_IMAGE_PATH, "rb") as img:
            await message.reply_photo(
                photo=img,
                caption=caption,
                reply_markup=buttons
            )

    # ----------------------------------------------------
    # MAIN HELP SCREEN (photo → photo edit OK)
    # ----------------------------------------------------
    @app.on_callback_query(filters.regex("^help_main$"))
    async def help_main(client, callback):

        caption = """
📖 **Smash & Pass - Help**

Choose a module below:
"""

        buttons = InlineKeyboardMarkup(get_help_buttons())

        with open(HELP_IMAGE_PATH, "rb") as img:
            await callback.message.edit_media(
                InputMediaPhoto(media=img, caption=caption),
                reply_markup=buttons
            )

        await callback.answer()

    # ----------------------------------------------------
    # MODULE HELP (photo → photo edit OK)
    # ----------------------------------------------------
    @app.on_callback_query(filters.regex(r"^help_(\w+)$"))
    async def help_module(client, callback):

        module_name = callback.data.split("_", 1)[1]

        if module_name == "close":
            await callback.message.delete()
            return

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

    # ----------------------------------------------------
    # CLOSE
    # ----------------------------------------------------
    @app.on_callback_query(filters.regex("^help_close$"))
    async def help_close(client, callback):
        await callback.message.delete()
        await callback.answer("Closed!")
