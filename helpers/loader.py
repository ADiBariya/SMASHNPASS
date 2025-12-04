# helpers/loader.py - Auto Module Loader

import os
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Auto-loads all modules from the modules directory"""
    
    def __init__(self, app):
        self.app = app
        self.modules_dir = Path("modules")
        self.loaded_modules: Dict[str, Any] = {}
        self.help_data: Dict[str, Dict] = {}
        
    def load_all_modules(self) -> int:
        """Load all modules from modules directory"""
        if not self.modules_dir.exists():
            logger.error(f"Modules directory not found: {self.modules_dir}")
            return 0
        
        loaded_count = 0
        
        for file in sorted(self.modules_dir.glob("*.py")):
            if file.name.startswith("_"):
                continue
                
            module_name = file.stem
            
            try:
                module = importlib.import_module(f"modules.{module_name}")
                
                # Check if module has setup function
                if hasattr(module, "setup"):
                    module.setup(self.app)
                    logger.info(f"✅ Loaded module: {module_name} (with setup)")
                else:
                    logger.info(f"✅ Loaded module: {module_name}")
                
                self.loaded_modules[module_name] = module
                
                # Load help data if available
                if hasattr(module, "HELP"):
                    self.help_data[module_name] = module.HELP
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to load module {module_name}: {e}")
                
        return loaded_count
    
    def reload_module(self, module_name: str) -> bool:
        """Reload a specific module"""
        try:
            if module_name in self.loaded_modules:
                module = importlib.reload(self.loaded_modules[module_name])
                
                if hasattr(module, "setup"):
                    module.setup(self.app)
                
                self.loaded_modules[module_name] = module
                
                if hasattr(module, "HELP"):
                    self.help_data[module_name] = module.HELP
                
                logger.info(f"🔄 Reloaded module: {module_name}")
                return True
            else:
                return self.load_module(module_name)
                
        except Exception as e:
            logger.error(f"❌ Failed to reload module {module_name}: {e}")
            return False
    
    def load_module(self, module_name: str) -> bool:
        """Load a specific module"""
        try:
            module = importlib.import_module(f"modules.{module_name}")
            
            if hasattr(module, "setup"):
                module.setup(self.app)
            
            self.loaded_modules[module_name] = module
            
            if hasattr(module, "HELP"):
                self.help_data[module_name] = module.HELP
            
            logger.info(f"✅ Loaded module: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load module {module_name}: {e}")
            return False
    
    def unload_module(self, module_name: str) -> bool:
        """Unload a specific module"""
        if module_name in self.loaded_modules:
            del self.loaded_modules[module_name]
            
            if module_name in self.help_data:
                del self.help_data[module_name]
            
            logger.info(f"🗑️ Unloaded module: {module_name}")
            return True
        return False
    
    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded module names"""
        return list(self.loaded_modules.keys())
    
    def get_help_data(self) -> Dict[str, Dict]:
        """Get all help data from modules"""
        return self.help_data
    
    def get_module_help(self, module_name: str) -> Dict:
        """Get help data for specific module"""
        return self.help_data.get(module_name, {})


class HelpManager:
    """Manages help data for inline help system"""
    
    def __init__(self, loader: ModuleLoader):
        self.loader = loader
    
    def get_main_help(self) -> str:
        """Get main help message"""
        help_text = "🎮 **Smash & Pass Waifu Bot**\n\n"
        help_text += "**Available Categories:**\n\n"
        
        for module_name, data in self.loader.get_help_data().items():
            if data.get("emoji") and data.get("name"):
                help_text += f"{data['emoji']} **{data['name']}**\n"
                if data.get("description"):
                    help_text += f"   └ {data['description']}\n"
        
        help_text += "\n📌 **Click buttons below to explore!**"
        return help_text
    
    def get_module_commands(self, module_name: str) -> str:
        """Get commands for a specific module"""
        data = self.loader.get_module_help(module_name)
        
        if not data:
            return "❌ Module not found!"
        
        help_text = f"{data.get('emoji', '📦')} **{data.get('name', module_name)}**\n\n"
        
        if data.get("description"):
            help_text += f"_{data['description']}_\n\n"
        
        help_text += "**Commands:**\n"
        
        for cmd, desc in data.get("commands", {}).items():
            help_text += f"• `/{cmd}` - {desc}\n"
        
        if data.get("usage"):
            help_text += f"\n**Usage:**\n{data['usage']}"
        
        return help_text
    
    def get_help_buttons(self) -> list:
        """Generate help buttons for all modules"""
        from pyrogram.types import InlineKeyboardButton
        
        buttons = []
        row = []
        
        for module_name, data in self.loader.get_help_data().items():
            emoji = data.get("emoji", "📦")
            name = data.get("name", module_name)
            
            btn = InlineKeyboardButton(
                f"{emoji} {name}",
                callback_data=f"help_{module_name}"
            )
            row.append(btn)
            
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        return buttons