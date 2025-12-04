# helpers/utils.py - Utility Functions

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class WaifuManager:
    """Manages waifu data from JSON file"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_waifus()
        return cls._instance
    
    def _load_waifus(self):
        """Load waifus from JSON file"""
        json_path = Path("waifus.json")
        
        if not json_path.exists():
            self.waifus = []
            self.rarity_colors = {}
            self.rarity_weights = {}
            return
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.waifus = data.get("waifus", [])
        self.rarity_colors = data.get("rarity_colors", {})
        self.rarity_weights = data.get("rarity_weights", {})
    
    def reload_waifus(self):
        """Reload waifus from JSON file"""
        self._load_waifus()
    
    def get_random_waifu(self) -> Optional[Dict]:
        """Get a random waifu based on rarity weights"""
        if not self.waifus:
            return None
        
        # Group waifus by rarity
        rarity_groups = {}
        for waifu in self.waifus:
            rarity = waifu.get("rarity", "common")
            if rarity not in rarity_groups:
                rarity_groups[rarity] = []
            rarity_groups[rarity].append(waifu)
        
        # Select rarity based on weights
        rarities = list(self.rarity_weights.keys())
        weights = list(self.rarity_weights.values())
        
        if not rarities:
            return random.choice(self.waifus)
        
        selected_rarity = random.choices(rarities, weights=weights, k=1)[0]
        
        # Get random waifu from selected rarity
        if selected_rarity in rarity_groups and rarity_groups[selected_rarity]:
            return random.choice(rarity_groups[selected_rarity])
        
        return random.choice(self.waifus)
    
    def get_waifu_by_id(self, waifu_id: int) -> Optional[Dict]:
        """Get waifu by ID"""
        for waifu in self.waifus:
            if waifu.get("id") == waifu_id:
                return waifu
        return None
    
    def get_waifu_by_name(self, name: str) -> Optional[Dict]:
        """Get waifu by name (case insensitive)"""
        name_lower = name.lower()
        for waifu in self.waifus:
            if waifu.get("name", "").lower() == name_lower:
                return waifu
        return None
    
    def search_waifus(self, query: str) -> List[Dict]:
        """Search waifus by name or anime"""
        query_lower = query.lower()
        results = []
        
        for waifu in self.waifus:
            if (query_lower in waifu.get("name", "").lower() or 
                query_lower in waifu.get("anime", "").lower()):
                results.append(waifu)
        
        return results
    
    def get_all_waifus(self) -> List[Dict]:
        """Get all waifus"""
        return self.waifus
    
    def get_waifus_by_rarity(self, rarity: str) -> List[Dict]:
        """Get all waifus of a specific rarity"""
        return [w for w in self.waifus if w.get("rarity") == rarity]
    
    def get_waifus_by_anime(self, anime: str) -> List[Dict]:
        """Get all waifus from a specific anime"""
        anime_lower = anime.lower()
        return [w for w in self.waifus if anime_lower in w.get("anime", "").lower()]
    
    def get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for rarity"""
        return self.rarity_colors.get(rarity, "⚪")
    
    def get_total_count(self) -> int:
        """Get total number of waifus"""
        return len(self.waifus)
    
    def add_waifu(self, waifu_data: Dict) -> bool:
        """Add a new waifu to the list"""
        if not waifu_data.get("id"):
            waifu_data["id"] = max([w.get("id", 0) for w in self.waifus], default=0) + 1
        
        self.waifus.append(waifu_data)
        self._save_waifus()
        return True
    
    def _save_waifus(self):
        """Save waifus to JSON file"""
        json_path = Path("waifus.json")
        data = {
            "waifus": self.waifus,
            "rarity_colors": self.rarity_colors,
            "rarity_weights": self.rarity_weights
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def get_waifu_manager() -> WaifuManager:
    """Get WaifuManager instance"""
    return WaifuManager()


class Utils:
    """General utility functions"""
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with commas"""
        return "{:,}".format(num)
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """Format seconds into readable time"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def get_progress_bar(current: int, total: int, length: int = 10) -> str:
        """Generate a progress bar"""
        if total == 0:
            percentage = 0
        else:
            percentage = current / total
        
        filled = int(length * percentage)
        empty = length - filled
        
        bar = "█" * filled + "░" * empty
        percent_text = f"{percentage * 100:.1f}%"
        
        return f"[{bar}] {percent_text}"
    
    @staticmethod
    def calculate_win(win_chance: int = 50) -> bool:
        """Calculate if user wins based on win chance"""
        return random.randint(1, 100) <= win_chance
    
    @staticmethod
    def get_streak_bonus(streak: int) -> int:
        """Calculate bonus coins based on win streak"""
        if streak < 3:
            return 0
        elif streak < 5:
            return 10
        elif streak < 10:
            return 25
        else:
            return 50
    
    @staticmethod
    def format_waifu_card(waifu: Dict, wm: WaifuManager) -> str:
        """Format waifu data into a nice card text"""
        rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
        
        text = f"""
{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {waifu.get('rarity', 'common').title()}
⚔️ **Power:** {waifu.get('power', 0)}

"""
        return text.strip()
    
    @staticmethod
    def format_collection_card(waifu: Dict, wm: WaifuManager) -> str:
        """Format collection waifu data"""
        rarity_emoji = wm.get_rarity_emoji(waifu.get("waifu_rarity", "common"))
        
        obtained_at = waifu.get("obtained_at")
        if isinstance(obtained_at, datetime):
            date_str = obtained_at.strftime("%d/%m/%Y")
        else:
            date_str = "Unknown"
        
        text = f"""
{rarity_emoji} **{waifu.get('waifu_name', 'Unknown')}**
📺 {waifu.get('waifu_anime', 'Unknown')}
⚔️ Power: {waifu.get('waifu_power', 0)}
📅 Obtained: {date_str}
"""
        return text.strip()
    
    @staticmethod
    def get_rarity_value(rarity: str) -> int:
        """Get numeric value for rarity (for sorting)"""
        rarity_values = {
            "common": 1,
            "rare": 2,
            "epic": 3,
            "legendary": 4
        }
        return rarity_values.get(rarity.lower(), 0)
    
    @staticmethod
    def mention_user(user_id: int, name: str) -> str:
        """Create a user mention"""
        return f"[{name}](tg://user?id={user_id})"