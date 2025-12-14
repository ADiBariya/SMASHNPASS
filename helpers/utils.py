# helpers/utils.py - Utility Functions
# helpers/utils.py - FINAL FIXED VERSION

import json
import random
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class WaifuManager:
    """Manages waifu data from JSON + Telegram channel"""

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
        self.waifus = []
        self.channel_waifus = []
        self.rarity_colors = {}
        self.rarity_weights = {}

        self._load_waifus()

    # ---------------- LOAD JSON ----------------
    def _load_waifus(self):
        json_path = Path("data/waifus.json")

        if not json_path.exists():
            self.waifus = self._get_default_waifus()
            self._save_waifus()
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}

        self.waifus = data.get("waifus", [])
        self.rarity_colors = data.get("rarity_colors", {})
        self.rarity_weights = data.get("rarity_weights", {})

    # ---------------- LOAD TG CHANNEL ----------------
    async def load_channel_waifus(self, client, channel_id: int):
        messages = []

        # Telegram returns NEWEST → OLDEST
        async for msg in client.get_chat_history(channel_id, limit=300):
            if msg.photo and msg.caption:
                messages.append(msg)

        # Reverse → OLDEST → NEWEST
        messages.reverse()

        waifus = []

        # Continue ID after JSON
        last_id = max([w.get("id", 0) for w in self.waifus], default=0)

        for msg in messages:
            try:
                if not msg.caption:
                    continue
                    
                lines = msg.caption.splitlines()
                if len(lines) < 3:
                    continue

                name = lines[0].replace("Name:", "").strip()
                anime = lines[1].replace("Anime:", "").strip()
                rarity = lines[2].replace("Rarity:", "").strip().lower()

                # Download image
                photo_path = await client.download_media(msg.photo.file_id)

                last_id += 1

                waifus.append({
                    "id": last_id,
                    "name": name,
                    "anime": anime,
                    "rarity": rarity,
                    "image": photo_path
                })

            except Exception as e:
                print("TG Load Error:", e)
                continue

        self.channel_waifus = waifus
        print(f"Loaded {len(waifus)} TG waifus")
    # ---------------- GET BY ID ----------------
    def get_waifu_by_id(self, waifu_id: int):
        try:
            wid = int(waifu_id)
        except:
            return None

        for w in self.waifus + self.channel_waifus:
            if int(w.get("id", 0)) == wid:
                return w
        return None

    # ---------------- GET ALL ----------------
    def get_all_waifus(self):
        return self.waifus + self.channel_waifus

    # ---------------- RARITY EMOJI ----------------
    def get_rarity_emoji(self, rarity: str) -> str:
        rarity = (rarity or "").lower()

        # Try to read from JSON
        if rarity in self.rarity_colors:
            return self.rarity_colors.get(rarity, "❓")

        default = {
            "common": "⚪",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }
        return default.get(rarity, "❓")

    # ---------------- DEFAULT WAIFUS ----------------
    def _get_default_waifus(self):
        return [
            {
                "id": 1,
                "name": "Boa Hancock",
                "anime": "One Piece",
                "rarity": "legendary",
                "image": "https://files.catbox.moe/iu35t6.jpg"
            }
        ]

    # ---------------- SAVE ----------------
    def _save_waifus(self):
        json_path = Path("data/waifus.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "waifus": self.waifus,
                    "rarity_colors": self.rarity_colors,
                    "rarity_weights": self.rarity_weights
                }, f, indent=4, ensure_ascii=False)

            print("Saved waifus.json")
        except Exception as e:
            print("Save error:", e)


# SINGLETON
def get_waifu_manager() -> WaifuManager:
    return WaifuManager()


class Utils:
    """General utility functions"""

    @staticmethod
    def format_number(num: int) -> str:
        return "{:,}".format(num)

    @staticmethod
    def format_time(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds//60}m {seconds%60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @staticmethod
    def get_progress_bar(current: int, total: int, length: int = 10) -> str:
        percentage = 0 if total == 0 else current / total
        filled = int(length * percentage)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {percentage*100:.1f}%"

    @staticmethod
    def calculate_win(win_chance: int = 50) -> bool:
        return random.randint(1, 100) <= win_chance

    @staticmethod
    def get_streak_bonus(streak: int) -> int:
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
        wm = wm or get_waifu_manager()
        rarity_emoji = wm.get_rarity_emoji(waifu.get("rarity", "common"))
        return f"""
{rarity_emoji} **{waifu.get('name','Unknown')}**

📺 **Anime:** {waifu.get('anime','Unknown')}
💎 **Rarity:** {waifu.get('rarity','common').title()}
""".strip()

    @staticmethod
    def mention_user(uid: int, name: str) -> str:
        return f"[{name}](tg://user?id={uid})"

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

    # ---------------- RANDOM WAIFU ----------------
def get_random_waifu(self):
        """Return a random waifu from merged JSON + TG waifus"""
        all_waifus = self.get_all_waifus()
        if not all_waifus:
            return None
        return random.choice(all_waifus)

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
