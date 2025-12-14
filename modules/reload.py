# modules/reloadwaifu.py

from pyrogram import Client, filters
from pyrogram.types import Message
import config
from helpers.utils import get_waifu_manager

__MODULE__ = "Reload Waifus"
__HELP__ = "/reload - Reload TG waifus without restarting bot"


@Client.on_message(filters.command(["reload"], ["/", ".", "!"]))
async def reload_waifus(client: Client, message: Message):

    # Owner only
    if message.from_user.id != config.OWNER_ID:
        return await message.reply("❌ Owner only command.")

    wm = get_waifu_manager()
    status = await message.reply("⏳ Reloading waifus from Telegram channel…")

    try:
        # 🔥 reuse SAME user session started in main.py
        from main import user  

        await wm.load_channel_waifus(user, config.TG_WAIFU_CHANNEL)

        await status.edit_text("✅ **Reload complete!**\nNew waifus loaded.")

    except Exception as e:
        await status.edit_text(f"❌ **Reload failed:**\n`{e}`")
