from functools import wraps
from pyrogram.types import Message, CallbackQuery
from database import db
from config import OWNER_ID, SUDO_USERS
import time
import asyncio

# Rate limiting storage
_rate_limits = {}
_cooldowns = {}


def owner_only(func):
    """Decorator to restrict command to owner only"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user_id = update.from_user.id
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
            reply_func = update.answer
        else:
            return
        
        if user_id != OWNER_ID:
            if isinstance(update, CallbackQuery):
                return await reply_func("❌ Owner only!", show_alert=True)
            return await reply_func("❌ This command is owner only!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def sudo_only(func):
    """Decorator to restrict command to sudo users"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user_id = update.from_user.id
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
            reply_func = update.answer
        else:
            return
        
        if user_id != OWNER_ID and user_id not in SUDO_USERS:
            if isinstance(update, CallbackQuery):
                return await reply_func("❌ Sudo users only!", show_alert=True)
            return await reply_func("❌ This command is for sudo users only!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def admin_only(func):
    """Decorator to restrict command to admins (owner + sudo)"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user_id = update.from_user.id
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
            reply_func = update.answer
        else:
            return
        
        if user_id != OWNER_ID and user_id not in SUDO_USERS:
            if isinstance(update, CallbackQuery):
                return await reply_func("❌ Admins only!", show_alert=True)
            return await reply_func("❌ This command is for admins only!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def rate_limit(seconds: int = 3, key: str = None):
    """
    Rate limit decorator
    
    Args:
        seconds: Cooldown in seconds
        key: Custom key for rate limiting (default: function name)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            if isinstance(update, Message):
                user_id = update.from_user.id
                reply_func = update.reply_text
            elif isinstance(update, CallbackQuery):
                user_id = update.from_user.id
                reply_func = update.answer
            else:
                return
            
            # Create unique key
            limit_key = f"{key or func.__name__}_{user_id}"
            current_time = time.time()
            
            if limit_key in _rate_limits:
                time_passed = current_time - _rate_limits[limit_key]
                if time_passed < seconds:
                    remaining = seconds - time_passed
                    if isinstance(update, CallbackQuery):
                        return await reply_func(
                            f"⏳ Wait {remaining:.1f}s",
                            show_alert=True
                        )
                    return await reply_func(f"⏳ Please wait **{remaining:.1f}** seconds!")
            
            _rate_limits[limit_key] = current_time
            return await func(client, update, *args, **kwargs)
        return wrapper
    return decorator


def cooldown(seconds: int = 60, per_user: bool = True):
    """
    Cooldown decorator with per-user or global option
    
    Args:
        seconds: Cooldown duration
        per_user: If True, cooldown is per user. If False, global cooldown
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            if isinstance(update, Message):
                user_id = update.from_user.id
                reply_func = update.reply_text
            elif isinstance(update, CallbackQuery):
                user_id = update.from_user.id
                reply_func = update.answer
            else:
                return
            
            # Create key
            if per_user:
                cd_key = f"{func.__name__}_{user_id}"
            else:
                cd_key = func.__name__
            
            current_time = time.time()
            
            if cd_key in _cooldowns:
                time_passed = current_time - _cooldowns[cd_key]
                if time_passed < seconds:
                    remaining = seconds - time_passed
                    
                    # Format time nicely
                    if remaining >= 3600:
                        time_str = f"{remaining/3600:.1f}h"
                    elif remaining >= 60:
                        time_str = f"{remaining/60:.1f}m"
                    else:
                        time_str = f"{remaining:.0f}s"
                    
                    if isinstance(update, CallbackQuery):
                        return await reply_func(
                            f"⏳ Cooldown: {time_str}",
                            show_alert=True
                        )
                    return await reply_func(f"⏳ This command is on cooldown! Wait **{time_str}**")
            
            _cooldowns[cd_key] = current_time
            return await func(client, update, *args, **kwargs)
        return wrapper
    return decorator


def ensure_user(func):
    """Ensure user exists in database before executing"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user_id = update.from_user.id
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
        else:
            return
        
        # Ensure user exists
        await db.get_user(user_id)
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def check_ban(func):
    """Check if user is banned"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user_id = update.from_user.id
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
            reply_func = update.answer
        else:
            return
        
        # Check ban status
        user_data = await db.get_user(user_id)
        
        if user_data.get("banned", False):
            if isinstance(update, CallbackQuery):
                return await reply_func("🚫 You are banned!", show_alert=True)
            return await reply_func("🚫 You are banned from using this bot!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def private_only(func):
    """Only allow in private chats"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            chat_type = update.chat.type
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            chat_type = update.message.chat.type
            reply_func = update.answer
        else:
            return
        
        if chat_type != "private":
            if isinstance(update, CallbackQuery):
                return await reply_func("❌ Use in PM only!", show_alert=True)
            return await reply_func("❌ This command only works in private chat!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def group_only(func):
    """Only allow in group chats"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            chat_type = update.chat.type
            reply_func = update.reply_text
        elif isinstance(update, CallbackQuery):
            chat_type = update.message.chat.type
            reply_func = update.answer
        else:
            return
        
        if chat_type not in ["group", "supergroup"]:
            if isinstance(update, CallbackQuery):
                return await reply_func("❌ Use in group only!", show_alert=True)
            return await reply_func("❌ This command only works in groups!")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def typing_action(func):
    """Show typing action while processing"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            chat_id = update.chat.id
            await client.send_chat_action(chat_id, "typing")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def log_command(func):
    """Log command usage"""
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, Message):
            user = update.from_user
            chat = update.chat
            command = update.text or "Unknown"
            
            print(f"[CMD] {user.first_name} ({user.id}) in {chat.title or 'PM'}: {command}")
        
        return await func(client, update, *args, **kwargs)
    return wrapper


def auto_delete(seconds: int = 30):
    """Auto delete bot response after specified seconds"""
    def decorator(func):
        @wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            result = await func(client, update, *args, **kwargs)
            
            # If function returns a message, schedule deletion
            if result and hasattr(result, 'id'):
                asyncio.create_task(delete_after(result, seconds))
            
            return result
        return wrapper
    return decorator


async def delete_after(message, seconds: int):
    """Helper to delete message after delay"""
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass


def require_coins(amount: int):
    """Require user to have minimum coins"""
    def decorator(func):
        @wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            if isinstance(update, Message):
                user_id = update.from_user.id
                reply_func = update.reply_text
            elif isinstance(update, CallbackQuery):
                user_id = update.from_user.id
                reply_func = update.answer
            else:
                return
            
            user_data = await db.get_user(user_id)
            coins = user_data.get("coins", 0)
            
            if coins < amount:
                if isinstance(update, CallbackQuery):
                    return await reply_func(
                        f"❌ Need {amount:,} coins! You have {coins:,}",
                        show_alert=True
                    )
                return await reply_func(
                    f"❌ You need **{amount:,}** coins!\n"
                    f"You have: **{coins:,}** coins"
                )
            
            return await func(client, update, *args, **kwargs)
        return wrapper
    return decorator


def require_collection(min_waifus: int = 1):
    """Require user to have minimum waifus in collection"""
    def decorator(func):
        @wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            if isinstance(update, Message):
                user_id = update.from_user.id
                reply_func = update.reply_text
            elif isinstance(update, CallbackQuery):
                user_id = update.from_user.id
                reply_func = update.answer
            else:
                return
            
            user_data = await db.get_user(user_id)
            collection = user_data.get("collection", [])
            
            if len(collection) < min_waifus:
                if isinstance(update, CallbackQuery):
                    return await reply_func(
                        f"❌ Need {min_waifus} waifus!",
                        show_alert=True
                    )
                return await reply_func(
                    f"❌ You need at least **{min_waifus}** waifu(s)!\n"
                    f"Use `/smash` to get waifus."
                )
            
            return await func(client, update, *args, **kwargs)
        return wrapper
    return decorator