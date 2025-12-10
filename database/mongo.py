# database/mongo.py - MongoDB Operations (FIXED & ENHANCED v2)

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import config
import json
import os
from pymongo import UpdateOne
import logging

# Setup logger
logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.DB_NAME]
        
        # Collections
        self.users = self.db["users"]
        self.collections = self.db["collections"]
        self.trades = self.db["trades"]
        self.stats = self.db["stats"]
        self.cooldowns = self.db["cooldowns"]
        # Global Waifus Registry
        self.waifus = self.db["waifus"]
        
        # Create indexes for faster queries
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimization"""
        try:
            self.users.create_index("user_id", unique=True)
            self.collections.create_index("user_id")
            self.collections.create_index([("user_id", 1), ("waifu_id", 1)])
            self.collections.create_index([("user_id", 1), ("waifu_id", 1), ("waifu_image", 1)])
            self.collections.create_index([("user_id", 1), ("waifu_rarity", 1)])
            self.cooldowns.create_index("user_id")
            self.cooldowns.create_index([("user_id", 1), ("action", 1)], unique=True)
            self.waifus.create_index("id", unique=True)
            self.waifus.create_index("name")
            self.trades.create_index("from_user")
            self.trades.create_index("to_user")
            self.trades.create_index("expires_at")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    #  USER OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        try:
            return self.users.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create new user"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "display_name": first_name,
            "coins": 0,
            "total_smash": 0,
            "total_pass": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_earned": 0,
            "total_spent": 0,
            "daily_streak": 0,
            "favorite_waifu": None,
            "created_at": datetime.now(),
            "last_daily": None,
            "last_active": datetime.now()
        }
        try:
            self.users.update_one(
                {"user_id": user_id},
                {"$setOnInsert": user_data},
                upsert=True
            )
            logger.info(f"Created new user: {user_id}")
            return user_data
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return user_data
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Get user or create if not exists"""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, username, first_name)
        else:
            # Update user info if provided
            update_data = {"last_active": datetime.now()}
            if username:
                update_data["username"] = username
            if first_name:
                update_data["first_name"] = first_name
                if not user.get("display_name"):
                    update_data["display_name"] = first_name
            
            if update_data:
                self.users.update_one(
                    {"user_id": user_id},
                    {"$set": update_data}
                )
        return user or self.get_user(user_id)
    
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    def increment_user_stats(self, user_id: int, field: str, value: int = 1) -> bool:
        """Increment user statistics"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$inc": {field: value}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error incrementing stats for {user_id}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  COIN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def add_coins(self, user_id: int, amount: int) -> bool:
        """Add coins to user"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$inc": {"coins": amount, "total_earned": amount}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error adding coins to {user_id}: {e}")
            return False
    
    def remove_coins(self, user_id: int, amount: int) -> bool:
        """Remove coins from user (checks balance)"""
        try:
            user = self.get_user(user_id)
            if user and user.get("coins", 0) >= amount:
                result = self.users.update_one(
                    {"user_id": user_id},
                    {"$inc": {"coins": -amount, "total_spent": amount}}
                )
                return result.modified_count > 0
            return False
        except Exception as e:
            logger.error(f"Error removing coins from {user_id}: {e}")
            return False
    
    def get_coins(self, user_id: int) -> int:
        """Get user's coin balance"""
        user = self.get_user(user_id)
        return user.get("coins", 0) if user else 0
    
    def update_coins(self, user_id: int, amount: int) -> bool:
        """Update coins (positive to add, negative to remove)"""
        if amount >= 0:
            return self.add_coins(user_id, amount)
        else:
            return self.remove_coins(user_id, abs(amount))
    
    # ═══════════════════════════════════════════════════════════════════
    #  COLLECTION OPERATIONS (FIXED & ENHANCED)
    # ═══════════════════════════════════════════════════════════════════
    
    def _get_waifu_id(self, waifu_data: Dict) -> Optional[int]:
        """Extract waifu ID from any format"""
        wid = (
            waifu_data.get("id") or 
            waifu_data.get("waifu_id") or 
            waifu_data.get("_id")
        )
        
        if wid is None:
            return None
        
        try:
            return int(wid)
        except (ValueError, TypeError):
            return None
    
    def _get_waifu_field(self, waifu_data: Dict, field: str, default: Any = None) -> Any:
        """Get waifu field from any format"""
        value = waifu_data.get(field)
        if value is not None:
            return value
        
        value = waifu_data.get(f"waifu_{field}")
        if value is not None:
            return value
        
        return default
    
    def add_waifu_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """Add waifu to user collection"""
        waifu_id = self._get_waifu_id(waifu_data)
        
        if waifu_id is None:
            logger.warning(f"Cannot add waifu - no valid ID: {waifu_data}")
            return False
        
        waifu_name = self._get_waifu_field(waifu_data, "name", "Unknown")
        waifu_anime = self._get_waifu_field(waifu_data, "anime", "Unknown")
        waifu_rarity = self._get_waifu_field(waifu_data, "rarity", "common")
        waifu_image = self._get_waifu_field(waifu_data, "image", "")
        obtained_method = waifu_data.get("obtained_method") or waifu_data.get("obtained_from", "smash")
        
        collection_entry = {
            "user_id": user_id,
            "waifu_id": waifu_id,
            "waifu_name": waifu_name,
            "waifu_anime": waifu_anime,
            "waifu_rarity": str(waifu_rarity).lower(),
            "waifu_image": waifu_image,
            "obtained_at": datetime.now(),
            "obtained_method": obtained_method
        }
        
        try:
            self.collections.insert_one(collection_entry)
            logger.info(f"Added {waifu_name} (ID:{waifu_id}) to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding waifu: {e}")
            return False
    
    def add_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """Alias for add_waifu_to_collection"""
        return self.add_waifu_to_collection(user_id, waifu_data)
    
    def remove_from_collection(self, user_id: int, waifu_id) -> bool:
        """Remove ONE waifu from collection"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid waifu_id for removal: {waifu_id}")
            return False
        
        result = self.collections.delete_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"Removed waifu ID:{waifu_id} from user {user_id}")
            return True
        return False
    
    def remove_from_collection_by_image(self, user_id: int, waifu_id: int, image: str) -> bool:
        """Remove ONE waifu matching ID + image combination"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid waifu_id for removal: {waifu_id}")
            return False
        
        result = self.collections.delete_one({
            "user_id": user_id,
            "waifu_id": waifu_id,
            "waifu_image": image
        })
        
        if result.deleted_count > 0:
            logger.info(f"Removed waifu ID:{waifu_id} with specific image from user {user_id}")
            return True
        
        return self.remove_from_collection(user_id, waifu_id)
    
    def remove_waifu_from_collection(self, user_id: int, waifu_id) -> bool:
        """Alias for remove_from_collection"""
        return self.remove_from_collection(user_id, waifu_id)
    
    def get_full_collection(self, user_id: int) -> List[Dict]:
        """Get user's complete collection - NO LIMIT"""
        try:
            collection = list(
                self.collections.find({"user_id": user_id})
                .sort("obtained_at", -1)
            )
            logger.debug(f"Retrieved {len(collection)} waifus for user {user_id}")
            return collection
        except Exception as e:
            logger.error(f"Error getting collection for {user_id}: {e}")
            return []
    
    def get_user_collection(self, user_id: int, page: int = 0, per_page: int = 0) -> List[Dict]:
        """Get user's waifu collection - returns ALL if no pagination specified"""
        try:
            if page <= 0 or per_page <= 0:
                # Return ALL waifus
                return self.get_full_collection(user_id)
            
            skip = (page - 1) * per_page
            return list(
                self.collections.find({"user_id": user_id})
                .sort("obtained_at", -1)
                .skip(skip)
                .limit(per_page)
            )
        except Exception as e:
            logger.error(f"Error getting paginated collection for {user_id}: {e}")
            return []
    
    def get_collection_count(self, user_id: int) -> int:
        """Get total waifus in user collection"""
        try:
            count = self.collections.count_documents({"user_id": user_id})
            return count
        except Exception as e:
            logger.error(f"Error counting collection for {user_id}: {e}")
            return 0
    
    def get_collection_by_rarity(self, user_id: int) -> Dict[str, int]:
        """Get collection count grouped by rarity"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": {"$toLower": "$waifu_rarity"},
                    "count": {"$sum": 1}
                }}
            ]
            results = list(self.collections.aggregate(pipeline))
            
            rarity_counts = {
                "common": 0,
                "rare": 0,
                "epic": 0,
                "legendary": 0
            }
            
            for r in results:
                rarity = r.get("_id", "common")
                if rarity in rarity_counts:
                    rarity_counts[rarity] = r.get("count", 0)
            
            return rarity_counts
        except Exception as e:
            logger.error(f"Error getting rarity counts for {user_id}: {e}")
            return {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
    
    def check_waifu_owned(self, user_id: int, waifu_id) -> bool:
        """Check if user owns a specific waifu"""
        try:
            waifu_id = int(waifu_id)
            return self.collections.find_one({
                "user_id": user_id,
                "waifu_id": waifu_id
            }) is not None
        except (ValueError, TypeError):
            return False
    
    def get_waifu_from_collection(self, user_id: int, waifu_id) -> Optional[Dict]:
        """Get specific waifu from user collection"""
        try:
            waifu_id = int(waifu_id)
            return self.collections.find_one({
                "user_id": user_id,
                "waifu_id": waifu_id
            })
        except (ValueError, TypeError):
            return None
    
    def count_waifu_owned(self, user_id: int, waifu_id) -> int:
        """Count how many of a specific waifu user owns"""
        try:
            waifu_id = int(waifu_id)
            return self.collections.count_documents({
                "user_id": user_id,
                "waifu_id": waifu_id
            })
        except (ValueError, TypeError):
            return 0
    
    def count_waifu_variant_owned(self, user_id: int, waifu_id: int, image: str) -> int:
        """Count how many of a specific waifu variant user owns"""
        try:
            waifu_id = int(waifu_id)
            return self.collections.count_documents({
                "user_id": user_id,
                "waifu_id": waifu_id,
                "waifu_image": image
            })
        except (ValueError, TypeError):
            return 0
    
    def get_user_collection_by_rarity(self, user_id: int, rarity: str) -> List[Dict]:
        """Get user waifus filtered by rarity"""
        try:
            return list(self.collections.find({
                "user_id": user_id,
                "waifu_rarity": rarity.lower()
            }))
        except Exception as e:
            logger.error(f"Error filtering collection by rarity: {e}")
            return []
    
    def get_duplicate_waifus(self, user_id: int) -> List[Dict]:
        """Get duplicate waifus in collection"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$waifu_id",
                    "count": {"$sum": 1},
                    "waifu_name": {"$first": "$waifu_name"},
                    "waifu_rarity": {"$first": "$waifu_rarity"}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            return list(self.collections.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting duplicates: {e}")
            return []
    
    def get_duplicate_variants(self, user_id: int) -> List[Dict]:
        """Get duplicate waifu variants"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": {"waifu_id": "$waifu_id", "waifu_image": "$waifu_image"},
                    "count": {"$sum": 1},
                    "waifu_name": {"$first": "$waifu_name"},
                    "waifu_rarity": {"$first": "$waifu_rarity"}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            return list(self.collections.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting duplicate variants: {e}")
            return []
    
    def get_best_waifu(self, user_id: int) -> Optional[Dict]:
        """Get user's best (highest rarity) waifu"""
        try:
            # Priority order for rarity
            for rarity in ["legendary", "epic", "rare", "common"]:
                waifu = self.collections.find_one({
                    "user_id": user_id,
                    "waifu_rarity": rarity
                })
                if waifu:
                    return waifu
            return None
        except Exception as e:
            logger.error(f"Error getting best waifu for {user_id}: {e}")
            return None
    
    def cleanup_invalid_waifus(self, user_id: int = None) -> int:
        """Remove entries with invalid waifu_id"""
        query = {
            "$or": [
                {"waifu_id": None},
                {"waifu_id": {"$exists": False}},
                {"waifu_id": 0},
                {"waifu_name": None},
                {"waifu_name": ""},
                {"waifu_name": "Unknown"}
            ]
        }
        
        if user_id:
            query["user_id"] = user_id
        
        try:
            result = self.collections.delete_many(query)
            logger.info(f"Cleaned up {result.deleted_count} invalid entries")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up invalid waifus: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  COOLDOWN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_cooldown(self, user_id: int, action: str) -> Optional[datetime]:
        """Get cooldown for user action"""
        try:
            cooldown = self.cooldowns.find_one({
                "user_id": user_id,
                "action": action
            })
            if cooldown:
                return cooldown.get("expires_at")
            return None
        except Exception as e:
            logger.error(f"Error getting cooldown: {e}")
            return None
    
    def set_cooldown(self, user_id: int, action: str, seconds: int) -> bool:
        """Set cooldown for user action"""
        try:
            expires_at = datetime.now() + timedelta(seconds=seconds)
            self.cooldowns.update_one(
                {"user_id": user_id, "action": action},
                {"$set": {"expires_at": expires_at}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}")
            return False
    
    def check_cooldown(self, user_id: int, action: str) -> Tuple[bool, int]:
        """Check if user is on cooldown. Returns (is_on_cooldown, remaining_seconds)"""
        expires_at = self.get_cooldown(user_id, action)
        if expires_at and expires_at > datetime.now():
            remaining = (expires_at - datetime.now()).total_seconds()
            return True, int(remaining)
        return False, 0
    
    def clear_cooldown(self, user_id: int, action: str) -> bool:
        """Clear a specific cooldown"""
        try:
            result = self.cooldowns.delete_one({
                "user_id": user_id,
                "action": action
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error clearing cooldown: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  GLOBAL WAIFU REGISTRY
    # ═══════════════════════════════════════════════════════════════════
    
    def upsert_waifu(self, waifu_data: Dict) -> bool:
        """Update or Insert a waifu definition into global registry"""
        try:
            wid = waifu_data.get("id")
            if not wid:
                return False
                
            self.waifus.update_one(
                {"id": wid},
                {"$set": waifu_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting waifu: {e}")
            return False

    def sync_waifus_from_json(self, json_path: str = "data/waifus.json") -> int:
        """Syncs the JSON file content to MongoDB 'waifus' collection"""
        if not os.path.exists(json_path):
            logger.warning(f"{json_path} not found. Skipping sync.")
            return 0
            
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            waifu_list = data.get("waifus", [])
            if not waifu_list:
                return 0
                
            operations = []
            for w in waifu_list:
                if "id" in w:
                    op = UpdateOne({"id": w["id"]}, {"$set": w}, upsert=True)
                    operations.append(op)
            
            if operations:
                result = self.waifus.bulk_write(operations)
                logger.info(f"Synced {len(waifu_list)} waifus to MongoDB")
                return len(waifu_list)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to sync waifus from JSON: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════
    #  DAILY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def can_claim_daily(self, user_id: int) -> Tuple[bool, int]:
        """Check if user can claim daily reward"""
        user = self.get_user(user_id)
        if not user or not user.get("last_daily"):
            return True, 0
        
        last_daily = user["last_daily"]
        next_daily = last_daily + timedelta(hours=24)
        
        if datetime.now() >= next_daily:
            return True, 0
        
        remaining = (next_daily - datetime.now()).total_seconds()
        return False, int(remaining)
    
    def claim_daily(self, user_id: int, coins: int) -> Tuple[bool, int]:
        """Claim daily reward - Returns (success, streak)"""
        user = self.get_or_create_user(user_id)
        
        streak = 1
        if user and user.get("last_daily"):
            last = user["last_daily"]
            hours_since = (datetime.now() - last).total_seconds() / 3600
            
            if hours_since <= 48:
                streak = user.get("daily_streak", 0) + 1
            else:
                streak = 1
        
        self.add_coins(user_id, coins)
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "last_daily": datetime.now(),
                "daily_streak": streak
            }},
            upsert=True
        )
        return True, streak
    
    def get_daily_streak(self, user_id: int) -> int:
        """Get user's daily streak"""
        user = self.get_user(user_id)
        return user.get("daily_streak", 0) if user else 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  FAVORITE WAIFU OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def set_favorite_waifu(self, user_id: int, waifu_id: int) -> bool:
        """Set user's favorite waifu"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": {"favorite_waifu": waifu_id}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error setting favorite: {e}")
            return False
    
    def get_favorite_waifu(self, user_id: int) -> Optional[int]:
        """Get user's favorite waifu ID"""
        user = self.get_user(user_id)
        return user.get("favorite_waifu") if user else None
    
    def remove_favorite_waifu(self, user_id: int) -> bool:
        """Remove user's favorite waifu"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$unset": {"favorite_waifu": ""}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing favorite: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  LEADERBOARD OPERATIONS (ENHANCED FOR PROFILE MODULE)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_top_collectors(self, limit: int = 10) -> List[Dict]:
        """Get top users by collection size"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1}
                }},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            results = list(self.collections.aggregate(pipeline))
            
            if not results:
                logger.info("No collectors found in database")
                return []
            
            # Add user details
            formatted_results = []
            for result in results:
                user_id = result["_id"]
                
                if user_id is None:
                    continue
                    
                user = self.get_user(user_id)
                
                formatted = {
                    "user_id": user_id,
                    "collection_count": result["count"],
                    "_collection_count": result["count"],  # Alias for compatibility
                    "count": result["count"],
                    "username": None,
                    "first_name": None,
                    "display_name": None,
                    "coins": 0
                }
                
                if user:
                    formatted["username"] = user.get("username")
                    formatted["first_name"] = user.get("first_name")
                    formatted["display_name"] = user.get("display_name")
                    formatted["coins"] = user.get("coins", 0)
                
                formatted_results.append(formatted)
            
            logger.info(f"Found {len(formatted_results)} top collectors")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in get_top_collectors: {e}")
            return []
    
    def get_top_winners(self, limit: int = 10) -> List[Dict]:
        """Get top users by wins"""
        try:
            results = list(
                self.users.find(
                    {"total_wins": {"$gt": 0}},
                    {
                        "user_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "display_name": 1,
                        "total_wins": 1,
                        "coins": 1
                    }
                )
                .sort("total_wins", -1)
                .limit(limit)
            )
            
            if not results:
                logger.info("No winners found in database")
                return []
            
            logger.info(f"Found {len(results)} top winners")
            return results
            
        except Exception as e:
            logger.error(f"Error in get_top_winners: {e}")
            return []
    
    def get_top_rich(self, limit: int = 10) -> List[Dict]:
        """Get top users by coins"""
        try:
            results = list(
                self.users.find(
                    {"coins": {"$gt": 0}},
                    {
                        "user_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "display_name": 1,
                        "coins": 1,
                        "total_wins": 1
                    }
                )
                .sort("coins", -1)
                .limit(limit)
            )
            
            if not results:
                logger.info("No rich users found in database")
                return []
            
            logger.info(f"Found {len(results)} top rich users")
            return results
            
        except Exception as e:
            logger.error(f"Error in get_top_rich: {e}")
            return []
    
    def get_user_rank(self, user_id: int) -> int:
        """Get user's global rank by collection + coins"""
        try:
            # Get all users with collection counts
            pipeline = [
                {"$group": {
                    "_id": "$user_id",
                    "collection_count": {"$sum": 1}
                }},
                {"$match": {"_id": {"$ne": None}}}
            ]
            collection_data = {r["_id"]: r["collection_count"] for r in self.collections.aggregate(pipeline)}
            
            # Get all users
            all_users = list(self.users.find({}, {"user_id": 1, "coins": 1}))
            
            # Calculate net worth for each user
            user_scores = []
            for user in all_users:
                uid = user.get("user_id")
                if uid is None:
                    continue
                coins = user.get("coins", 0)
                collection_count = collection_data.get(uid, 0)
                # Simple scoring: coins + (collection_count * 100)
                score = coins + (collection_count * 100)
                user_scores.append({"user_id": uid, "score": score})
            
            # Sort by score
            user_scores.sort(key=lambda x: x["score"], reverse=True)
            
            # Find user's rank
            for i, u in enumerate(user_scores, 1):
                if u["user_id"] == user_id:
                    return i
            
            return 0
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0
    
    def get_all_users_with_stats(self) -> List[Dict]:
        """Get all users with their collection stats - for leaderboard"""
        try:
            # Get collection counts
            pipeline = [
                {"$group": {
                    "_id": "$user_id",
                    "collection_count": {"$sum": 1}
                }},
                {"$match": {"_id": {"$ne": None}}}
            ]
            collection_data = {r["_id"]: r["collection_count"] for r in self.collections.aggregate(pipeline)}
            
            # Get all users
            all_users = list(self.users.find({}))
            
            # Merge data
            users_with_stats = []
            for user in all_users:
                user_id = user.get("user_id")
                if user_id is None:
                    continue
                
                user_stats = dict(user)
                user_stats["_collection_count"] = collection_data.get(user_id, 0)
                user_stats["collection_count"] = collection_data.get(user_id, 0)
                
                # Calculate collection value (simple: count * 50)
                user_stats["_collection_value"] = user_stats["_collection_count"] * 50
                user_stats["_net_worth"] = user.get("coins", 0) + user_stats["_collection_value"]
                
                users_with_stats.append(user_stats)
            
            return users_with_stats
        except Exception as e:
            logger.error(f"Error getting users with stats: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    #  TRADE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def create_trade(self, from_user: int, to_user: int, waifu_id: int, 
                     waifu_name: str, coins: int = 0) -> str:
        """Create a trade request"""
        trade_data = {
            "from_user": from_user,
            "to_user": to_user,
            "waifu_id": waifu_id,
            "waifu_name": waifu_name,
            "coins": coins,
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5)
        }
        result = self.trades.insert_one(trade_data)
        return str(result.inserted_id)
    
    def get_pending_trades(self, user_id: int) -> List[Dict]:
        """Get pending trades for user"""
        return list(self.trades.find({
            "to_user": user_id,
            "status": "pending",
            "expires_at": {"$gt": datetime.now()}
        }))
    
    def accept_trade(self, trade_id: str) -> bool:
        """Accept a trade"""
        from bson import ObjectId
        
        try:
            trade = self.trades.find_one({"_id": ObjectId(trade_id)})
        except:
            return False
        
        if not trade or trade["status"] != "pending":
            return False
        
        if trade["expires_at"] < datetime.now():
            return False
        
        waifu = self.get_waifu_from_collection(trade["from_user"], trade["waifu_id"])
        if waifu:
            self.remove_from_collection(trade["from_user"], trade["waifu_id"])
            
            new_waifu = {
                "id": waifu.get("waifu_id"),
                "name": waifu.get("waifu_name"),
                "anime": waifu.get("waifu_anime"),
                "rarity": waifu.get("waifu_rarity"),
                "image": waifu.get("waifu_image"),
                "obtained_method": "trade"
            }
            self.add_to_collection(trade["to_user"], new_waifu)
        
        if trade.get("coins", 0) > 0:
            self.add_coins(trade["from_user"], trade["coins"])
            self.remove_coins(trade["to_user"], trade["coins"])
        
        self.trades.update_one(
            {"_id": ObjectId(trade_id)},
            {"$set": {"status": "accepted"}}
        )
        return True
    
    def reject_trade(self, trade_id: str) -> bool:
        """Reject a trade"""
        from bson import ObjectId
        
        try:
            result = self.trades.update_one(
                {"_id": ObjectId(trade_id)},
                {"$set": {"status": "rejected"}}
            )
            return result.modified_count > 0
        except:
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  INVENTORY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def add_to_inventory(self, user_id: int, item: Dict) -> bool:
        """Add item to user inventory"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$push": {"inventory": item}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error adding to inventory: {e}")
            return False
    
    def get_inventory(self, user_id: int) -> List[Dict]:
        """Get user's inventory"""
        user = self.get_user(user_id)
        return user.get("inventory", []) if user else []
    
    def remove_from_inventory(self, user_id: int, item_id: str) -> bool:
        """Remove item from inventory"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$pull": {"inventory": {"id": item_id}}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing from inventory: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  GLOBAL STATS (ENHANCED)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_global_stats(self) -> Dict:
        """Get global bot statistics"""
        try:
            total_users = self.users.count_documents({})
            total_waifus = self.collections.count_documents({})
            
            # Aggregate smash/pass totals
            stats_pipeline = [
                {"$group": {
                    "_id": None,
                    "total_smash": {"$sum": {"$ifNull": ["$total_smash", 0]}},
                    "total_pass": {"$sum": {"$ifNull": ["$total_pass", 0]}},
                    "total_wins": {"$sum": {"$ifNull": ["$total_wins", 0]}},
                    "total_coins": {"$sum": {"$ifNull": ["$coins", 0]}}
                }}
            ]
            
            result = list(self.users.aggregate(stats_pipeline))
            
            if result:
                stats = {
                    "total_users": total_users,
                    "total_waifus": total_waifus,
                    "total_waifus_collected": total_waifus,
                    "total_smashes": result[0].get("total_smash", 0) or result[0].get("total_wins", 0),
                    "total_passes": result[0].get("total_pass", 0),
                    "total_coins": result[0].get("total_coins", 0)
                }
            else:
                stats = {
                    "total_users": total_users,
                    "total_waifus": total_waifus,
                    "total_waifus_collected": total_waifus,
                    "total_smashes": 0,
                    "total_passes": 0,
                    "total_coins": 0
                }
            
            logger.info(f"Global stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {
                "total_users": 0,
                "total_waifus": 0,
                "total_waifus_collected": 0,
                "total_smashes": 0,
                "total_passes": 0,
                "total_coins": 0
            }
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        try:
            return list(self.users.find({}))
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def get_total_users(self) -> int:
        """Get total user count"""
        try:
            return self.users.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  DEBUG METHODS
    # ═══════════════════════════════════════════════════════════════════
    
    def debug_check_data(self) -> Dict:
        """Debug method to check database state"""
        try:
            users_count = self.users.count_documents({})
            collections_count = self.collections.count_documents({})
            
            # Sample user
            sample_user = self.users.find_one({})
            
            # Sample collection entry
            sample_collection = self.collections.find_one({})
            
            # Users with coins
            users_with_coins = self.users.count_documents({"coins": {"$gt": 0}})
            
            # Users with wins
            users_with_wins = self.users.count_documents({"total_wins": {"$gt": 0}})
            
            # Unique collectors
            unique_collectors = len(self.collections.distinct("user_id"))
            
            return {
                "users_count": users_count,
                "collections_count": collections_count,
                "unique_collectors": unique_collectors,
                "sample_user_fields": list(sample_user.keys()) if sample_user else [],
                "sample_collection_fields": list(sample_collection.keys()) if sample_collection else [],
                "users_with_coins": users_with_coins,
                "users_with_wins": users_with_wins
            }
        except Exception as e:
            logger.error(f"Error in debug check: {e}")
            return {"error": str(e)}
    
    def debug_user_collection(self, user_id: int) -> Dict:
        """Debug a specific user's collection"""
        try:
            user = self.get_user(user_id)
            collection = self.get_full_collection(user_id)
            rarity_counts = self.get_collection_by_rarity(user_id)
            
            return {
                "user_exists": user is not None,
                "user_coins": user.get("coins", 0) if user else 0,
                "collection_count": len(collection),
                "rarity_counts": rarity_counts,
                "sample_waifus": [
                    {
                        "id": w.get("waifu_id"),
                        "name": w.get("waifu_name"),
                        "rarity": w.get("waifu_rarity")
                    }
                    for w in collection[:5]
                ]
            }
        except Exception as e:
            logger.error(f"Error in debug_user_collection: {e}")
            return {"error": str(e)}


# Create global instance
db = Database()
