from pyrogram import Client, filters
from pyrogram.types import Message
import config
from helpers.utils import get_waifu_manager
from core.user_client import user

__MODULE__ = "𝐑𝐞𝐥𝐨𝐚𝐝"
__HELP__ = "/reload - Reload TG waifus without restarting bot"


@Client.on_message(filters.command(["reload"], ["/", ".", "!"]))
async def reload_waifus(client: Client, message: Message):

    allowed = [config.OWNER_ID, 5162885921]
    if message.from_user.id not in allowed:
        return await message.reply("❌ Owner only command.")

    wm = get_waifu_manager()
    status = await message.reply("⏳ Reloading waifus from Telegram channel…")

    try:
        # 🔥 REUSE RUNNING USER CLIENT
        await wm.load_channel_waifus(user, config.TG_WAIFU_CHANNEL)
        await status.edit_text("✅ **Reload complete!**")

    except Exception as e:
        await status.edit_text(f"❌ **Reload failed:**\n`{e}`")
