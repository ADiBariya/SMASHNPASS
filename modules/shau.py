

from pyrogram import Client, filters
from pyrogram.types import Message
from database import db

@Client.on_message(filters.group, group=-999)
async def track_group_activity(client: Client, message: Message):
    """Track all group activity for statistics"""
    try:
        if not message.chat:
            return
            
        chat = message.chat
        
        # Track/update group in database
        db.get_or_create_group(
            chat_id=chat.id,
            title=chat.title,
            username=getattr(chat, 'username', None)
        )
        
        # Increment message count
        db.increment_group_stats(chat.id, "message_count", 1)
        
    except Exception:
        pass  # Silent fail - don't interrupt message flow
