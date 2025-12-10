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
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_waifus()
    
    def _load_waifus(self):
        """Load waifus from JSON file"""
        # ✅ FIXED: Correct path to data folder
        json_path = Path("data/waifus.json")
        
        print(f"📂 Looking for waifus at: {json_path.absolute()}")
        
        if not json_path.exists():
            print(f"⚠️ waifus.json not found! Creating default waifus...")
            self.waifus = self._get_default_waifus()
            self.rarity_colors = {
                "common": "⚪",
                "epic": "🟣",
                "legendary": "🟡",
                "rare": "🔵"
            }
            self.rarity_weights = {
                "common": 50,
                "epic": 15,
                "legendary": 5,
                "rare": 30
            }
            # Save default waifus
            self._save_waifus()
            return
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.waifus = data.get("waifus", [])
            self.rarity_colors = data.get("rarity_colors", {
                "common": "⚪",
                "epic": "🟣",
                "legendary": "🟡",
                "rare": "🔵"
            })
            self.rarity_weights = data.get("rarity_weights", {
                "common": 50,
                "epic": 15,
                "legendary": 5,
                "rare": 30
            })
            print(f"✅ Loaded {len(self.waifus)} waifus successfully!")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Error: {e}")
            self.waifus = self._get_default_waifus()
            self.rarity_colors = {"common": "⚪", "epic": "🟣", "legendary": "🟡", "rare": "🔵"}
            self.rarity_weights = {"common": 50, "epic": 15, "legendary": 5, "rare": 30}
        except Exception as e:
            print(f"❌ Error loading waifus: {e}")
            self.waifus = []
            self.rarity_colors = {}
            self.rarity_weights = {}
    
    def _get_default_waifus(self) -> List[Dict]:
        """Return default waifus if file not found"""
        return [
            {
                "id": 1,
                "name": "Boa hancock",
                "anime": "One Piece",
                "rarity": "legendary",
                "image": "https://files.catbox.moe/iu35t6.jpg"
            },
            {
                "id": 2,
                "name": "Nami",
                "anime": "One Piece",
                "rarity": "legendary",
                "image": "https://files.catbox.moe/reh8mz.jpg"
            },
            {
                "id": 3,
                "name": "Robin",
                "anime": "One piece",
                "rarity": "epic",
                "image": "https://files.catbox.moe/0oqwqt.jpg"
            },
            {
                "id": 4,
                "name": "Yamato",
                "anime": "One piece",
                "rarity": "epic",
                "image": "https://files.catbox.moe/5rnwlt.jpg"
            },
            {
                "id": 5,
                "name": "Marin",
                "anime": "My Dress up Darling",
                "rarity": "legendary",
                "image": "https://files.catbox.moe/86wqd9.jpg"
            }
        ]
    
    def reload_waifus(self):
        """Reload waifus from JSON file"""
        self._load_waifus()
    
    def get_random_waifu(self) -> Optional[Dict]:
        """Get a random waifu based on rarity weights"""
        if not self.waifus:
            print("❌ No waifus in list!")
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
        
        if not rarities or not weights:
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
        default_emojis = {
            "common": "⚪",
            "epic": "🟣",
            "legendary": "🟡",
            "rare": "🔵"
        }
        return self.rarity_colors.get(rarity, default_emojis.get(rarity, "⚪"))
    
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
        # ✅ FIXED: Correct path
        json_path = Path("data/waifus.json")
        
        # Create data folder if not exists
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "waifus": self.waifus,
            "rarity_colors": self.rarity_colors,
            "rarity_weights": self.rarity_weights
        }
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ Saved {len(self.waifus)} waifus to {json_path}")
        except Exception as e:
            print(f"❌ Error saving waifus: {e}")


# Singleton getter function
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
    def format_waifu_card(waifu: Dict, wm: WaifuManager = None) -> str:
        """Format waifu data into a nice card text (without power)"""
        if wm is None:
            wm = get_waifu_manager()
        rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
        
        text = f"""
{rarity_emoji} **{waifu.get('name', 'Unknown')}**

📺 **Anime:** {waifu.get('anime', 'Unknown')}
💎 **Rarity:** {waifu.get('rarity', 'common').title()}
"""
        return text.strip()
    
    @staticmethod
    def format_collection_card(waifu: Dict, wm: WaifuManager = None) -> str:
        """Format collection waifu data (without power)"""
        if wm is None:
            wm = get_waifu_manager()
        rarity_emoji = wm.get_rarity_emoji(waifu.get("waifu_rarity", "common"))
        
        obtained_at = waifu.get("obtained_at")
        if isinstance(obtained_at, datetime):
            date_str = obtained_at.strftime("%d/%m/%Y")
        else:
            date_str = "Unknown"
        
        text = f"""
{rarity_emoji} **{waifu.get('waifu_name', 'Unknown')}**
📺 {waifu.get('waifu_anime', 'Unknown')}
📅 Obtained: {date_str}
"""
        return text.strip()
    
    @staticmethod
    def get_rarity_value(rarity: str) -> int:
        """Get numeric value for rarity (for sorting) - Updated order"""
        rarity_values = {
            "common": 1,
            "epic": 2,
            "legendary": 3,
            "rare": 4
        }
        return rarity_values.get(rarity.lower(), 0)
    
    @staticmethod
    def mention_user(user_id: int, name: str) -> str:
        """Create a user mention"""
        return f"[{name}](tg://user?id={user_id})"


# ═══════════════════════════════════════════════════════════════════
#  🔥 STANDALONE WRAPPER FUNCTIONS (For Direct Import)
# ═══════════════════════════════════════════════════════════════════

# Global instance
_waifu_manager = None

def _get_manager() -> WaifuManager:
    """Get or create WaifuManager instance"""
    global _waifu_manager
    if _waifu_manager is None:
        _waifu_manager = WaifuManager()
    return _waifu_manager


def load_waifus() -> List[Dict]:
    """Load and return all waifus from JSON"""
    wm = _get_manager()
    return wm.get_all_waifus()


def save_waifus(waifus: List[Dict]):
    """Save waifus to JSON file"""
    wm = _get_manager()
    wm.waifus = waifus
    wm._save_waifus()


def get_random_waifu() -> Optional[Dict]:
    """Get a random waifu based on rarity weights"""
    wm = _get_manager()
    return wm.get_random_waifu()


def get_waifu_by_id(waifu_id: int) -> Optional[Dict]:
    """Get waifu by ID"""
    wm = _get_manager()
    return wm.get_waifu_by_id(waifu_id)


def get_waifu_by_name(name: str) -> Optional[Dict]:
    """Get waifu by name"""
    wm = _get_manager()
    return wm.get_waifu_by_name(name)


def search_waifus(query: str) -> List[Dict]:
    """Search waifus by name or anime"""
    wm = _get_manager()
    return wm.search_waifus(query)


def get_waifus_by_rarity(rarity: str) -> List[Dict]:
    """Get waifus by rarity"""
    wm = _get_manager()
    return wm.get_waifus_by_rarity(rarity)


def get_waifus_by_anime(anime: str) -> List[Dict]:
    """Get waifus by anime"""
    wm = _get_manager()
    return wm.get_waifus_by_anime(anime)


def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity"""
    wm = _get_manager()
    return wm.get_rarity_emoji(rarity)


def get_rarity_value(rarity: str) -> int:
    """Get coin value for rarity - Updated with new order"""
    values = {
        "common": 10,
        "epic": 25,
        "legendary": 50,
        "rare": 100
    }
    return values.get(rarity.lower(), 10)


def calculate_collection_value(collection: List[Dict]) -> int:
    """Calculate total collection value"""
    total = 0
    for waifu in collection:
        rarity = waifu.get("rarity") or waifu.get("waifu_rarity", "common")
        total += get_rarity_value(rarity)
    return total


def reload_waifus():
    """Reload waifus from JSON file"""
    wm = _get_manager()
    wm.reload_waifus()


def add_waifu(waifu_data: Dict) -> bool:
    """Add a new waifu"""
    wm = _get_manager()
    return wm.add_waifu(waifu_data)


def get_total_waifus() -> int:
    """Get total number of waifus"""
    wm = _get_manager()
    return wm.get_total_count()


# ═══════════════════════════════════════════════════════════════════
#  📦 UTILITY WRAPPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def format_number(num: int) -> str:
    """Format number with commas"""
    return Utils.format_number(num)


def format_time(seconds: int) -> str:
    """Format seconds to readable time"""
    return Utils.format_time(seconds)


def get_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Generate progress bar"""
    return Utils.get_progress_bar(current, total, length)


def calculate_win(win_chance: int = 50) -> bool:
    """Calculate if user wins"""
    return Utils.calculate_win(win_chance)


def get_streak_bonus(streak: int) -> int:
    """Get streak bonus coins"""
    return Utils.get_streak_bonus(streak)


def format_waifu_card(waifu: Dict) -> str:
    """Format waifu card"""
    wm = _get_manager()
    return Utils.format_waifu_card(waifu, wm)


def format_collection_card(waifu: Dict) -> str:
    """Format collection card"""
    wm = _get_manager()
    return Utils.format_collection_card(waifu, wm)


def mention_user(user_id: int, name: str) -> str:
    """Create user mention"""
    return Utils.mention_user(user_id, name)
