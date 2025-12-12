from pyrogram import Client, filters
from config import OWNER_ID
from database import db

@Client.on_message(filters.command("checkcd") & filters.user(OWNER_ID))
async def check_cooldown_cmd(client, message):
    user_id = message.from_user.id
    status = db.check_cooldown(user_id, "smash")
    await message.reply(f"Cooldown status:\n\n{status}")

@Client.on_message(filters.command("clearcd") & filters.user(OWNER_ID))
async def clear_cooldown_cmd(client, message):
    db.cooldowns.delete_many({})
    await message.reply("✅ All cooldowns cleared!")
