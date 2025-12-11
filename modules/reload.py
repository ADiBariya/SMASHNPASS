# modules/reloadwaifu.py

from pyrogram import Client, filters
from pyrogram.types import Message

import config
from helpers.utils import get_waifu_manager

__MODULE__ = "Reload Waifus"
__HELP__ = "/reload - Reload TG waifus without restarting bot"


@Client.on_message(filters.command(["reload"], ["/", ".", "!"]))
async def reload_waifus(client: Client, message: Message):

    if message.from_user.id != config.OWNER_ID:
        return await message.reply("❌ Owner only command.")

    wm = get_waifu_manager()

    await message.reply("⏳ Reloading waifus from Telegram channel…")

    # ⭐ Correct User session client (use SAME STRING SESSION as main.py)
    user = Client(
        name="user_reload",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.USER_SESSION    # <-- IMPORTANT FIX
    )

    try:
        await user.start()  # No OTP, no input needed

        await wm.load_channel_waifus(user, config.TG_WAIFU_CHANNEL)

        # Do NOT stop user session permanently
        await user.stop()  # safe

        await message.reply("✅ **Reload complete!**\nNew waifus loaded.")

    except Exception as e:
        await message.reply(f"❌ Error reloading: `{e}`")
