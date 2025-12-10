# database/mongo.py - MongoDB Operations (FIXED)

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import config
import json
import os
from pymongo import UpdateOne


class Database:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.DB_NAME]
        
        # Collections
        self.users = self.db["users"]
        self.collections = self.db["collections"]
        self.trades = self.db["trades"]
        self.stats = self.db["stats"]
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
            # NEW: Index for image-based queries
            self.collections.create_index([("user_id", 1), ("waifu_id", 1), ("waifu_image", 1)])
            self.cooldowns.create_index("user_id")
            self.waifus.create_index("id", unique=True)
            self.waifus.create_index("name")
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    #  USER OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        return self.users.find_one({"user_id": user_id})
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create new user"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
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
            "last_daily": None
        }
        self.users.insert_one(user_data)
        return user_data
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Get user or create if not exists"""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, username, first_name)
        else:
            # Update user info if provided
            if username or first_name:
                update_data = {}
                if username:
                    update_data["username"] = username
                if first_name:
                    update_data["first_name"] = first_name
                if update_data:
                    self.users.update_one(
                        {"user_id": user_id},
                        {"$set": update_data}
                    )
        return user
    
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def increment_user_stats(self, user_id: int, field: str, value: int = 1) -> bool:
        """Increment user statistics"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$inc": {field: value}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    # ═══════════════════════════════════════════════════════════════════
    #  COIN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def add_coins(self, user_id: int, amount: int) -> bool:
        """Add coins to user"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"coins": amount, "total_earned": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    def remove_coins(self, user_id: int, amount: int) -> bool:
        """Remove coins from user (checks balance)"""
        user = self.get_user(user_id)
        if user and user.get("coins", 0) >= amount:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$inc": {"coins": -amount, "total_spent": amount}}
            )
            return result.modified_count > 0
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
    #  COLLECTION OPERATIONS (FIXED)
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
        """Get waifu field from any format (handles both id/waifu_id style)"""
        # Try direct field first
        value = waifu_data.get(field)
        if value is not None:
            return value
        
        # Try with waifu_ prefix
        value = waifu_data.get(f"waifu_{field}")
        if value is not None:
            return value
        
        return default
    
    def add_waifu_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """Add waifu to user collection"""
        # Extract waifu ID
        waifu_id = self._get_waifu_id(waifu_data)
        
        if waifu_id is None:
            print(f"⚠️ [DB] Cannot add waifu - no valid ID: {waifu_data}")
            return False
        
        # Extract all fields (handles both formats)
        waifu_name = self._get_waifu_field(waifu_data, "name", "Unknown")
        waifu_anime = self._get_waifu_field(waifu_data, "anime", "Unknown")
        waifu_rarity = self._get_waifu_field(waifu_data, "rarity", "common")
        waifu_image = self._get_waifu_field(waifu_data, "image", "")
        obtained_method = waifu_data.get("obtained_method") or waifu_data.get("obtained_from", "smash")
        
        # Validate name
        if not waifu_name or waifu_name == "Unknown":
            print(f"⚠️ [DB] Waifu name is Unknown for ID {waifu_id}")
        
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
            print(f"✅ [DB] Added {waifu_name} (ID:{waifu_id}) to user {user_id}")
            return True
        except Exception as e:
            print(f"❌ [DB] Error adding waifu: {e}")
            return False
    
    def add_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """Alias for add_waifu_to_collection"""
        return self.add_waifu_to_collection(user_id, waifu_data)
    
    def remove_from_collection(self, user_id: int, waifu_id) -> bool:
        """Remove ONE waifu from collection (not all duplicates)"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            print(f"⚠️ [DB] Invalid waifu_id for removal: {waifu_id}")
            return False
        
        # Delete only ONE instance
        result = self.collections.delete_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
        
        if result.deleted_count > 0:
            print(f"✅ [DB] Removed waifu ID:{waifu_id} from user {user_id}")
            return True
        return False
    
    def remove_from_collection_by_image(self, user_id: int, waifu_id: int, image: str) -> bool:
        """Remove ONE waifu matching ID + image combination (for different variants)"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            print(f"⚠️ [DB] Invalid waifu_id for removal: {waifu_id}")
            return False
        
        # Delete only ONE instance matching both waifu_id AND image
        result = self.collections.delete_one({
            "user_id": user_id,
            "waifu_id": waifu_id,
            "waifu_image": image
        })
        
        if result.deleted_count > 0:
            print(f"✅ [DB] Removed waifu ID:{waifu_id} with specific image from user {user_id}")
            return True
        
        # Fallback: Try without image match (for older entries without image stored)
        print(f"⚠️ [DB] No exact image match, trying ID only fallback...")
        return self.remove_from_collection(user_id, waifu_id)
    
    def remove_waifu_from_collection(self, user_id: int, waifu_id) -> bool:
        """Alias for remove_from_collection"""
        return self.remove_from_collection(user_id, waifu_id)
    
    def get_full_collection(self, user_id: int) -> List[Dict]:
        """Get user's complete collection"""
        return list(
            self.collections.find({"user_id": user_id})
            .sort("obtained_at", -1)
        )
    
    def get_user_collection(self, user_id: int, page: int = 1, per_page: int = 10) -> List[Dict]:
        """Get user's waifu collection with pagination"""
        skip = (page - 1) * per_page
        return list(
            self.collections.find({"user_id": user_id})
            .sort("obtained_at", -1)
            .skip(skip)
            .limit(per_page)
        )
    
    def get_collection_count(self, user_id: int) -> int:
        """Get total waifus in user collection"""
        return self.collections.count_documents({"user_id": user_id})
    
    def check_waifu_owned(self, user_id: int, waifu_id) -> bool:
        """Check if user owns a specific waifu"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            return False
        
        return self.collections.find_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        }) is not None
    
    def get_waifu_from_collection(self, user_id: int, waifu_id) -> Optional[Dict]:
        """Get specific waifu from user collection"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            return None
        
        return self.collections.find_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
    
    def count_waifu_owned(self, user_id: int, waifu_id) -> int:
        """Count how many of a specific waifu user owns"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            return 0
        
        return self.collections.count_documents({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
    
    def count_waifu_variant_owned(self, user_id: int, waifu_id: int, image: str) -> int:
        """Count how many of a specific waifu variant (same image) user owns"""
        try:
            waifu_id = int(waifu_id)
        except (ValueError, TypeError):
            return 0
        
        return self.collections.count_documents({
            "user_id": user_id,
            "waifu_id": waifu_id,
            "waifu_image": image
        })
    
    def get_user_collection_by_rarity(self, user_id: int, rarity: str) -> List[Dict]:
        """Get user waifus filtered by rarity"""
        return list(self.collections.find({
            "user_id": user_id,
            "waifu_rarity": rarity.lower()
        }))
    
    def get_duplicate_waifus(self, user_id: int) -> List[Dict]:
        """Get duplicate waifus in collection (by ID only)"""
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
    
    def get_duplicate_variants(self, user_id: int) -> List[Dict]:
        """Get duplicate waifu variants (same ID + same image)"""
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
        
        result = self.collections.delete_many(query)
        print(f"🧹 [DB] Cleaned up {result.deleted_count} invalid entries")
        return result.deleted_count
    
    # ═══════════════════════════════════════════════════════════════════
    #  COOLDOWN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_cooldown(self, user_id: int, action: str) -> Optional[datetime]:
        """Get cooldown for user action"""
        cooldown = self.cooldowns.find_one({
            "user_id": user_id,
            "action": action
        })
        if cooldown:
            return cooldown.get("expires_at")
        return None
    
    def set_cooldown(self, user_id: int, action: str, seconds: int) -> bool:
        """Set cooldown for user action"""
        expires_at = datetime.now() + timedelta(seconds=seconds)
        self.cooldowns.update_one(
            {"user_id": user_id, "action": action},
            {"$set": {"expires_at": expires_at}},
            upsert=True
        )
        return True
    
    def check_cooldown(self, user_id: int, action: str) -> Tuple[bool, int]:
        """Check if user is on cooldown. Returns (is_on_cooldown, remaining_seconds)"""
        expires_at = self.get_cooldown(user_id, action)
        if expires_at and expires_at > datetime.now():
            remaining = (expires_at - datetime.now()).total_seconds()
            return True, int(remaining)
        return False, 0
    
    def clear_cooldown(self, user_id: int, action: str) -> bool:
        """Clear a specific cooldown"""
        result = self.cooldowns.delete_one({
            "user_id": user_id,
            "action": action
        })
        return result.deleted_count > 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  GLOBAL WAIFU REGISTRY (SYNC/UPDATE)
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
            print(f"❌ [DB] Error upserting waifu: {e}")
            return False

    def sync_waifus_from_json(self, json_path: str = "data/waifus.json") -> int:
        """Syncs the JSON file content to MongoDB 'waifus' collection"""
        if not os.path.exists(json_path):
            print(f"⚠️ [DB] {json_path} not found. Skipping sync.")
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
                    # Upsert based on ID
                    op = UpdateOne({"id": w["id"]}, {"$set": w}, upsert=True)
                    operations.append(op)
            
            if operations:
                result = self.waifus.bulk_write(operations)
                print(f"✅ [DB] Synced {len(waifu_list)} waifus to MongoDB (Modified: {result.modified_count}, Upserted: {result.upserted_count})")
                return len(waifu_list)
            return 0
            
        except Exception as e:
            print(f"❌ [DB] Failed to sync waifus from JSON: {e}")
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
    
    def claim_daily(self, user_id: int, coins: int) -> bool:
        """Claim daily reward"""
        user = self.get_user(user_id)
        
        # Check streak
        streak = 1
        if user and user.get("last_daily"):
            last = user["last_daily"]
            hours_since = (datetime.now() - last).total_seconds() / 3600
            
            if hours_since <= 48:  # Within 48 hours = continue streak
                streak = user.get("daily_streak", 0) + 1
            else:
                streak = 1  # Reset streak
        
        self.add_coins(user_id, coins)
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "last_daily": datetime.now(),
                "daily_streak": streak
            }},
            upsert=True
        )
        return True
    
    def get_daily_streak(self, user_id: int) -> int:
        """Get user's daily streak"""
        user = self.get_user(user_id)
        return user.get("daily_streak", 0) if user else 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  FAVORITE WAIFU OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def set_favorite_waifu(self, user_id: int, waifu_id: int) -> bool:
        """Set user's favorite waifu"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$set": {"favorite_waifu": waifu_id}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    def get_favorite_waifu(self, user_id: int) -> Optional[int]:
        """Get user's favorite waifu ID"""
        user = self.get_user(user_id)
        return user.get("favorite_waifu") if user else None
    
    def remove_favorite_waifu(self, user_id: int) -> bool:
        """Remove user's favorite waifu"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$unset": {"favorite_waifu": ""}}
        )
        return result.modified_count > 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  LEADERBOARD OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_top_collectors(self, limit: int = 10) -> List[Dict]:
        """Get top users by collection size"""
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        results = list(self.collections.aggregate(pipeline))
        
        # Add user details
        formatted_results = []
        for result in results:
            user_id = result["_id"]
            user = self.get_user(user_id)
            
            formatted = {
                "user_id": user_id,
                "count": result["count"],
                "username": None,
                "first_name": None,
                "display_name": None
            }
            
            if user:
                formatted["username"] = user.get("username")
                formatted["first_name"] = user.get("first_name")
                formatted["display_name"] = user.get("display_name")
            
            formatted_results.append(formatted)
        
        return formatted_results
    
    def get_top_winners(self, limit: int = 10) -> List[Dict]:
        """Get top users by wins"""
        return list(
            self.users.find({"total_wins": {"$gt": 0}})
            .sort("total_wins", -1)
            .limit(limit)
        )
    
    def get_top_rich(self, limit: int = 10) -> List[Dict]:
        """Get top users by coins"""
        return list(
            self.users.find({"coins": {"$gt": 0}})
            .sort("coins", -1)
            .limit(limit)
        )
    
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
        
        # Transfer waifu
        waifu = self.get_waifu_from_collection(trade["from_user"], trade["waifu_id"])
        if waifu:
            self.remove_from_collection(trade["from_user"], trade["waifu_id"])
            
            # Prepare waifu data for new owner
            new_waifu = {
                "id": waifu.get("waifu_id"),
                "name": waifu.get("waifu_name"),
                "anime": waifu.get("waifu_anime"),
                "rarity": waifu.get("waifu_rarity"),
                "image": waifu.get("waifu_image"),
                "obtained_method": "trade"
            }
            self.add_to_collection(trade["to_user"], new_waifu)
        
        # Handle coins if any
        if trade.get("coins", 0) > 0:
            self.add_coins(trade["from_user"], trade["coins"])
            self.remove_coins(trade["to_user"], trade["coins"])
        
        # Update trade status
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
        result = self.users.update_one(
            {"user_id": user_id},
            {"$push": {"inventory": item}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    def get_inventory(self, user_id: int) -> List[Dict]:
        """Get user's inventory"""
        user = self.get_user(user_id)
        return user.get("inventory", []) if user else []
    
    def remove_from_inventory(self, user_id: int, item_id: str) -> bool:
        """Remove item from inventory"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$pull": {"inventory": {"id": item_id}}}
        )
        return result.modified_count > 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  GLOBAL STATS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_global_stats(self) -> Dict:
        """Get global bot statistics"""
        total_users = self.users.count_documents({})
        total_waifus = self.collections.count_documents({})
        
        smash_result = list(self.users.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$total_smash"}}}
        ]))
        
        pass_result = list(self.users.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$total_pass"}}}
        ]))
        
        return {
            "total_users": total_users,
            "total_waifus_collected": total_waifus,
            "total_smashes": smash_result[0]["total"] if smash_result else 0,
            "total_passes": pass_result[0]["total"] if pass_result else 0
        }
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        return list(self.users.find({}))
    
    def get_total_users(self) -> int:
        """Get total user count"""
        return self.users.count_documents({})


# Create global instance
db = Database()
