from pyrogram import Client, filters
from database import db
import config

@Client.on_message(filters.command("debugcol", prefixes=config.COMMAND_PREFIX))
async def debugcol(client, message):
    uid = message.from_user.id
    table_count = db.collections.count_documents({"user_id": uid})
    user = db.get_user(uid)
    embedded_count = len(user.get("collection", [])) if user and user.get("collection") else 0
    await message.reply_text(
        f"collections table: `{table_count}` docs\n"
        f"user.collection length: `{embedded_count}`"
    )
