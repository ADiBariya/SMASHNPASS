# modules/reloadwaifu.py

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import Client as UserClient

import config
from helpers.utils import get_waifu_manager


__MODULE__ = "Reload Waifus"
__HELP__ = "/reload - Reload TG waifus without restarting bot"


@Client.on_message(filters.command(["reload"], [".", "/", "!"]))
async def reload_waifus(client: Client, message: Message):

    # Only owner allowed
    if message.from_user.id != config.OWNER_ID:
        return await message.reply("❌ Owner only command.")

    wm = get_waifu_manager()

    await message.reply("⏳ Reloading waifus from Telegram channel…")

    # EXACT SAME USER SESSION CREATION USED IN main.py
    user = UserClient(
        "reload_session",
        api_id=config.API_ID,
        api_hash=config.API_HASH
    )

    try:
        await user.start()
        await wm.load_channel_waifus(user, config.TG_WAIFU_CHANNEL)
        await user.stop()

        await message.reply("✅ **Reload complete!**\nNew waifus loaded.")

    except Exception as e:
        await message.reply(f"❌ Error reloading: `{e}`")
