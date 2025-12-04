import os
import sys
import asyncio
import importlib
import logging
from pathlib import Path
from pyrogram import Client, idle, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Setup logging BEFORE imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Import config with error handling
try:
    from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
    logger.info("✅ Config loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load config: {e}")
    sys.exit(1)

# Import database with error handling
try:
    from database import db
    logger.info("✅ Database module loaded")
except Exception as e:
    logger.error(f"❌ Failed to load database module: {e}")
    sys.exit(1)

# Initialize bot WITHOUT auto-loading plugins
# (we'll load them manually to have better control)
app = Client(
    name="WaifuBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    # Remove auto-plugin loading
    # plugins=dict(root="modules")
)

# Store loaded modules info
LOADED_MODULES = {}
HELP_COMMANDS = {}


def load_modules():
    """Load all modules from modules folder"""
    modules_path = Path("modules")
    
    if not modules_path.exists():
        logger.warning("⚠️ Modules folder not found! Creating it...")
        modules_path.mkdir(exist_ok=True)
        return 0, 0
    
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
            logger.error(f"❌ Failed to load {module_name}: {e}", exc_info=True)
    
    logger.info(f"📦 Modules: {loaded} loaded, {failed} failed")
    return loaded, failed


def get_full_help():
    """Generate full help text"""
    if not LOADED_MODULES:
        return "📚 **WAIFU BOT HELP**\n\nNo modules loaded yet."
    
    help_text = "📚 **WAIFU BOT HELP**\n\n"
    
    for module_name, info in sorted(LOADED_MODULES.items()):
        help_text += f"**{info['name']}**\n"
        help_text += f"{info['help']}\n\n"
    
    return help_text


def get_module_list():
    """Get list of loaded modules"""
    text = "📦 **Loaded Modules**\n\n"
    
    if not LOADED_MODULES:
        text += "No modules loaded.\n"
    else:
        for module_name, info in sorted(LOADED_MODULES.items()):
            text += f"• **{info['name']}** (`{module_name}`)\n"
        
        text += f"\n📊 Total: {len(LOADED_MODULES)} modules"
    
    return text


# Help command handler
@app.on_message(filters.command(["help"], prefixes=[".", "/", "!"]))
async def help_handler(client, message):
    """Dynamic help handler"""
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
    if not LOADED_MODULES:
        await message.reply_text(
            "⚠️ No modules loaded yet.\n"
            "Please contact the bot administrator."
        )
        return
    
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
    data = callback.data.replace("help_", "")
    
    try:
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
    
    except Exception as e:
        logger.error(f"Error in help callback: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)


async def start_bot():
    """Start the bot"""
    logger.info("🚀 Starting Waifu Bot...")
    
    # Validate config
    if not all([API_ID, API_HASH, BOT_TOKEN, OWNER_ID]):
        logger.error("❌ Missing required config values!")
        return
    
    # Load modules
    loaded, failed = load_modules()
    
    # Connect to database with retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await db.connect()
            logger.info("📦 Database connected!")
            break
        except Exception as e:
            logger.error(f"❌ Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("❌ Could not connect to database after multiple attempts")
                # Continue anyway - some bots can work without DB
            else:
                await asyncio.sleep(2)
    
    # Start bot
    try:
        await app.start()
        logger.info("✅ Bot client started")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise
    
    # Get bot info
    try:
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
        except Exception as e:
            logger.warning(f"⚠️ Could not notify owner: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error getting bot info: {e}")
    
    # Keep bot running
    logger.info("✅ Bot is now running! Press Ctrl+C to stop.")
    await idle()
    
    # Cleanup
    await app.stop()
    logger.info("👋 Bot stopped!")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║         🎴 WAIFU SMASH BOT 🎴         ║
    ║                                       ║
    ║   Pyrogram Based | MongoDB | Fast     ║
    ╚═══════════════════════════════════════╝
    """)
    
    try:
        # Use asyncio.run() for better compatibility
        if sys.version_info >= (3, 7):
            asyncio.run(start_bot())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
