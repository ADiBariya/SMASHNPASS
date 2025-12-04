import os
import sys
import asyncio
import importlib
import logging
from pathlib import Path
from pyrogram import Client, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from database import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    name="WaifuBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="modules")
)

# Store loaded modules info
LOADED_MODULES = {}
HELP_COMMANDS = {}


def load_modules():
    """Load all modules from modules folder"""
    modules_path = Path("modules")
    
    if not modules_path.exists():
        logger.error("Modules folder not found!")
        return
    
    loaded = 0
    failed = 0
    
    for file in modules_path.glob("*.py"):
        if file.name.startswith("_"):
            continue
        
        module_name = file.stem
        
        try:
            module = importlib.import_module(f"modules.{module_name}")
            
            # Store module info
            LOADED_MODULES[module_name] = {
                "name": getattr(module, "__MODULE__", module_name.title()),
                "help": getattr(module, "__HELP__", "No help available.")
            }
            
            loaded += 1
            logger.info(f"✅ Loaded: {module_name}")
            
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to load {module_name}: {e}")
    
    logger.info(f"📦 Modules: {loaded} loaded, {failed} failed")
    return loaded, failed


def get_full_help():
    """Generate full help text"""
    help_text = "📚 **WAIFU BOT HELP**\n\n"
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        help_text += f"**{info['name']}**\n"
        help_text += f"{info['help']}\n\n"
    
    return help_text


def get_module_list():
    """Get list of loaded modules"""
    text = "📦 **Loaded Modules**\n\n"
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        text += f"• **{info['name']}** (`{module_name}`)\n"
    
    text += f"\n📊 Total: {len(LOADED_MODULES)} modules"
    return text


async def start_bot():
    """Start the bot"""
    logger.info("🚀 Starting Waifu Bot...")
    
    # Load modules
    load_modules()
    
    # Connect to database
    try:
        await db.connect()
        logger.info("📦 Database connected!")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    # Start bot
    await app.start()
    
    # Get bot info
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username}")
    
    # Notify owner
    try:
        await app.send_message(
            OWNER_ID,
            f"✅ **Bot Started!**\n\n"
            f"**Bot:** @{me.username}\n"
            f"**Modules:** {len(LOADED_MODULES)}\n"
            f"**Status:** Online"
        )
    except:
        pass
    
    # Keep bot running
    await idle()
    
    # Cleanup
    await app.stop()
    logger.info("👋 Bot stopped!")


# Help command handler (registered after modules)
from pyrogram import filters

@app.on_message(filters.command(["help"], prefixes=[".", "/", "!"]))
async def help_handler(client, message):
    """Dynamic help handler"""
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Check if specific module help is requested
    if len(message.command) > 1:
        module_name = message.command[1].lower()
        
        if module_name in LOADED_MODULES:
            info = LOADED_MODULES[module_name]
            await message.reply_text(
                f"📖 **{info['name']} Help**\n\n{info['help']}"
            )
        else:
            await message.reply_text("❌ Module not found!")
        return
    
    # Show module selection menu
    buttons = []
    row = []
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        row.append(
            InlineKeyboardButton(
                info["name"],
                callback_data=f"help_{module_name}"
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("📋 All Commands", callback_data="help_all")
    ])
    
    await message.reply_text(
        "📚 **Waifu Bot Help**\n\n"
        "Select a module to view its commands:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^help_"))
async def help_callback_handler(client, callback):
    """Handle help callbacks"""
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    data = callback.data.replace("help_", "")
    
    if data == "all":
        text = get_full_help()
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncated)"
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data == "back":
        buttons = []
        row = []
        
        for module_name, info in sorted(LOADED_MODULES.items()):
            row.append(
                InlineKeyboardButton(
                    info["name"],
                    callback_data=f"help_{module_name}"
                )
            )
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([
            InlineKeyboardButton("📋 All Commands", callback_data="help_all")
        ])
        
        await callback.message.edit_text(
            "📚 **Waifu Bot Help**\n\n"
            "Select a module to view its commands:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data in LOADED_MODULES:
        info = LOADED_MODULES[data]
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
        
        await callback.message.edit_text(
            f"📖 **{info['name']} Help**\n\n{info['help']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    await callback.answer()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║         🎴 WAIFU SMASH BOT 🎴         ║
    ║                                       ║
    ║   Pyrogram Based | MongoDB | Fast     ║
    ╚═══════════════════════════════════════╝
    """)
    
    try:
        asyncio.get_event_loop().run_until_complete(start_bot())
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
