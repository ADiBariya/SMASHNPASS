# database/mongo.py - MongoDB Operations (FULLY UPDATED & ENHANCED)

from pymongo import MongoClient, UpdateOne
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import config
import json
import os
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
        self.waifus = self.db["waifus"]
        self.groups = self.db["groups"]
        
        # Create indexes for faster queries
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimization"""
        try:
            # User indexes
            self.users.create_index("user_id", unique=True)
            self.users.create_index("last_active")
            self.users.create_index("coins")
            self.users.create_index("total_wins")
            self.users.create_index("banned")
            
            # Collection indexes
            self.collections.create_index("user_id")
            self.collections.create_index([("user_id", 1), ("waifu_id", 1)])
            self.collections.create_index([("user_id", 1), ("waifu_id", 1), ("waifu_image", 1)])
            self.collections.create_index("waifu_rarity")
            self.collections.create_index("obtained_at")
            
            # Cooldown indexes
            self.cooldowns.create_index("user_id")
            self.cooldowns.create_index([("user_id", 1), ("action", 1)])
            self.cooldowns.create_index("expires_at", expireAfterSeconds=0)
            
            # Waifu indexes
            self.waifus.create_index("id", unique=True)
            self.waifus.create_index("name")
            self.waifus.create_index("rarity")
            
            # Group indexes
            self.groups.create_index("chat_id", unique=True)
            self.groups.create_index("last_active")
            
            # Trade indexes
            self.trades.create_index("from_user")
            self.trades.create_index("to_user")
            self.trades.create_index("status")
            self.trades.create_index("expires_at")
            
            logger.info("Database indexes created successfully")
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
            "banned": False,
            "created_at": datetime.now(),
            "last_daily": None,
            "last_active": datetime.now()
        }
        try:
            self.users.insert_one(user_data)
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
                user.update(update_data)
        return user
    
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
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
    
    def get_active_users_count(self, hours: int = 24) -> int:
        """Get count of users active in the last X hours"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            return self.users.count_documents({
                "last_active": {"$gte": cutoff}
            })
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return 0
    
    def search_users(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by username or first_name"""
        try:
            return list(self.users.find({
                "$or": [
                    {"username": {"$regex": query, "$options": "i"}},
                    {"first_name": {"$regex": query, "$options": "i"}}
                ]
            }).limit(limit))
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    #  BAN/UNBAN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def ban_user(self, user_id: int, reason: str = None) -> bool:
        """Ban a user from the bot"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "banned": True,
                    "banned_at": datetime.now(),
                    "ban_reason": reason
                }},
                upsert=True
            )
            logger.info(f"Banned user: {user_id}")
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {"banned": False},
                    "$unset": {"banned_at": "", "ban_reason": ""}
                }
            )
            logger.info(f"Unbanned user: {user_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            user = self.get_user(user_id)
            return user.get("banned", False) if user else False
        except Exception as e:
            logger.error(f"Error checking ban status: {e}")
            return False
    
    def get_banned_users(self) -> List[Dict]:
        """Get list of banned users"""
        try:
            return list(self.users.find({"banned": True}))
        except Exception as e:
            logger.error(f"Error getting banned users: {e}")
            return []
    
    def get_banned_users_count(self) -> int:
        """Get count of banned users"""
        try:
            return self.users.count_documents({"banned": True})
        except Exception as e:
            logger.error(f"Error getting banned users count: {e}")
            return 0
    
    def reset_user(self, user_id: int) -> bool:
        """Reset all user data completely"""
        try:
            # Delete from users collection
            self.users.delete_one({"user_id": user_id})
            
            # Delete from collections
            deleted_waifus = self.collections.delete_many({"user_id": user_id})
            
            # Delete cooldowns
            self.cooldowns.delete_many({"user_id": user_id})
            
            # Delete trades
            self.trades.delete_many({
                "$or": [
                    {"from_user": user_id},
                    {"to_user": user_id}
                ]
            })
            
            logger.info(f"Reset all data for user: {user_id} (deleted {deleted_waifus.deleted_count} waifus)")
            return True
        except Exception as e:
            logger.error(f"Error resetting user {user_id}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    #  GROUP OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_group(self, chat_id: int) -> Optional[Dict]:
        """Get group data"""
        try:
            return self.groups.find_one({"chat_id": chat_id})
        except Exception as e:
            logger.error(f"Error getting group {chat_id}: {e}")
            return None
    
    def create_group(self, chat_id: int, title: str = None, username: str = None) -> Dict:
        """Create new group entry"""
        group_data = {
            "chat_id": chat_id,
            "title": title,
            "username": username,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "message_count": 0,
            "spawn_count": 0,
            "settings": {
                "spawn_enabled": True,
                "spawn_rate": 100,
                "notifications": True
            }
        }
        try:
            self.groups.update_one(
                {"chat_id": chat_id},
                {"$set": group_data},
                upsert=True
            )
            logger.info(f"Created/Updated group: {chat_id}")
            return group_data
        except Exception as e:
            logger.error(f"Error creating group {chat_id}: {e}")
            return group_data
    
    def get_or_create_group(self, chat_id: int, title: str = None, username: str = None) -> Dict:
        """Get group or create if not exists"""
        group = self.get_group(chat_id)
        if not group:
            group = self.create_group(chat_id, title, username)
        else:
            # Update last active and title
            update_data = {"last_active": datetime.now()}
            if title:
                update_data["title"] = title
            if username:
                update_data["username"] = username
            
            self.groups.update_one(
                {"chat_id": chat_id},
                {"$set": update_data}
            )
            group.update(update_data)
        return group
    
    def update_group(self, chat_id: int, update_data: Dict) -> bool:
        """Update group data"""
        try:
            result = self.groups.update_one(
                {"chat_id": chat_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating group {chat_id}: {e}")
            return False
    
    def increment_group_stats(self, chat_id: int, field: str, value: int = 1) -> bool:
        """Increment group statistics"""
        try:
            result = self.groups.update_one(
                {"chat_id": chat_id},
                {
                    "$inc": {field: value},
                    "$set": {"last_active": datetime.now()}
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error incrementing group stats: {e}")
            return False
    
    def get_total_groups(self) -> int:
        """Get total group count"""
        try:
            return self.groups.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total groups: {e}")
            return 0
    
    def get_active_groups_count(self, hours: int = 24) -> int:
        """Get count of groups active in the last X hours"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            return self.groups.count_documents({
                "last_active": {"$gte": cutoff}
            })
        except Exception as e:
            logger.error(f"Error getting active groups: {e}")
            return 0
    
    def get_all_groups(self) -> List[Dict]:
        """Get all groups"""
        try:
            return list(self.groups.find({}))
        except Exception as e:
            logger.error(f"Error getting all groups: {e}")
            return []
    
    def get_top_groups(self, limit: int = 10, sort_by: str = "spawn_count") -> List[Dict]:
        """Get top groups by specified field"""
        try:
            return list(
                self.groups.find({})
                .sort(sort_by, -1)
                .limit(limit)
            )
        except Exception as e:
            logger.error(f"Error getting top groups: {e}")
            return []
    
    def delete_group(self, chat_id: int) -> bool:
        """Delete a group from database"""
        try:
            result = self.groups.delete_one({"chat_id": chat_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting group {chat_id}: {e}")
            return False
    
    def update_group_settings(self, chat_id: int, settings: Dict) -> bool:
        """Update group settings"""
        try:
            result = self.groups.update_one(
                {"chat_id": chat_id},
                {"$set": {"settings": settings}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error updating group settings: {e}")
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
    
    def set_coins(self, user_id: int, amount: int) -> bool:
        """Set user's coin balance to specific amount"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": {"coins": amount}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error setting coins for {user_id}: {e}")
            return False
    
    def update_coins(self, user_id: int, amount: int) -> bool:
        """Update coins (positive to add, negative to remove)"""
        if amount >= 0:
            return self.add_coins(user_id, amount)
        else:
            return self.remove_coins(user_id, abs(amount))
    
    def transfer_coins(self, from_user: int, to_user: int, amount: int) -> bool:
        """Transfer coins between users"""
        if self.remove_coins(from_user, amount):
            if self.add_coins(to_user, amount):
                return True
            else:
                # Rollback if adding fails
                self.add_coins(from_user, amount)
        return False
    
    def get_total_coins_in_circulation(self) -> int:
        """Get total coins across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$coins", 0]}}}}
            ]
            result = list(self.users.aggregate(pipeline))
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total coins: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  COLLECTION OPERATIONS
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
        """Get user's complete collection"""
        try:
            return list(
                self.collections.find({"user_id": user_id})
                .sort("obtained_at", -1)
            )
        except Exception as e:
            logger.error(f"Error getting collection for {user_id}: {e}")
            return []
    
    def get_user_collection(self, user_id: int, page: int = 1, per_page: int = 10) -> List[Dict]:
        """Get user's waifu collection with pagination"""
        try:
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
            return self.collections.count_documents({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error counting collection for {user_id}: {e}")
            return 0
    
    def get_total_collected_waifus(self) -> int:
        """Get total waifus collected across all users"""
        try:
            return self.collections.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total collected waifus: {e}")
            return 0
    
    def get_unique_collectors_count(self) -> int:
        """Get count of unique users who have collected at least one waifu"""
        try:
            pipeline = [
                {"$group": {"_id": "$user_id"}},
                {"$count": "total"}
            ]
            result = list(self.collections.aggregate(pipeline))
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting unique collectors: {e}")
            return 0
    
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
    
    def get_rarity_distribution(self) -> Dict[str, int]:
        """Get distribution of collected waifus by rarity"""
        try:
            pipeline = [
                {"$group": {
                    "_id": {"$toLower": {"$ifNull": ["$waifu_rarity", "unknown"]}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            results = list(self.collections.aggregate(pipeline))
            
            distribution = {}
            for r in results:
                rarity = r["_id"] or "unknown"
                distribution[rarity] = r["count"]
            
            return distribution
        except Exception as e:
            logger.error(f"Error getting rarity distribution: {e}")
            return {}
    
    def get_user_rarity_distribution(self, user_id: int) -> Dict[str, int]:
        """Get rarity distribution for a specific user"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": {"$toLower": {"$ifNull": ["$waifu_rarity", "unknown"]}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            results = list(self.collections.aggregate(pipeline))
            
            distribution = {}
            for r in results:
                rarity = r["_id"] or "unknown"
                distribution[rarity] = r["count"]
            
            return distribution
        except Exception as e:
            logger.error(f"Error getting user rarity distribution: {e}")
            return {}
    
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
    
    def clear_all_cooldowns(self, user_id: int) -> int:
        """Clear all cooldowns for a user"""
        try:
            result = self.cooldowns.delete_many({"user_id": user_id})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error clearing all cooldowns: {e}")
            return 0
    
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

    def get_waifu_by_id(self, waifu_id: int) -> Optional[Dict]:
        """Get waifu from global registry by ID"""
        try:
            return self.waifus.find_one({"id": waifu_id})
        except Exception as e:
            logger.error(f"Error getting waifu {waifu_id}: {e}")
            return None
    
    def get_all_waifus(self) -> List[Dict]:
        """Get all waifus from registry"""
        try:
            return list(self.waifus.find({}))
        except Exception as e:
            logger.error(f"Error getting all waifus: {e}")
            return []
    
    def get_waifus_by_rarity(self, rarity: str) -> List[Dict]:
        """Get waifus by rarity from registry"""
        try:
            return list(self.waifus.find({"rarity": {"$regex": rarity, "$options": "i"}}))
        except Exception as e:
            logger.error(f"Error getting waifus by rarity: {e}")
            return []
    
    def get_total_waifus_in_registry(self) -> int:
        """Get total waifus in registry"""
        try:
            return self.waifus.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total waifus in registry: {e}")
            return 0

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
                logger.info(f"Synced {len(waifu_list)} waifus to MongoDB (Modified: {result.modified_count}, Upserted: {result.upserted_count})")
                return len(waifu_list)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to sync waifus from JSON: {e}")
            return 0
    
    def delete_waifu_from_registry(self, waifu_id: int) -> bool:
        """Delete a waifu from the registry"""
        try:
            result = self.waifus.delete_one({"id": waifu_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting waifu {waifu_id}: {e}")
            return False
    
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
        """Claim daily reward. Returns (success, streak)"""
        user = self.get_user(user_id)
        
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
    
    def reset_daily_streak(self, user_id: int) -> bool:
        """Reset user's daily streak"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": {"daily_streak": 0, "last_daily": None}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resetting daily streak: {e}")
            return False
    
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
    #  LEADERBOARD OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_top_collectors(self, limit: int = 10) -> List[Dict]:
        """Get top users by collection size"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            results = list(self.collections.aggregate(pipeline))
            
            if not results:
                return []
            
            formatted_results = []
            for result in results:
                user_id = result["_id"]
                
                if user_id is None:
                    continue
                    
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
                        "total_wins": 1
                    }
                )
                .sort("total_wins", -1)
                .limit(limit)
            )
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
                        "coins": 1
                    }
                )
                .sort("coins", -1)
                .limit(limit)
            )
            return results
        except Exception as e:
            logger.error(f"Error in get_top_rich: {e}")
            return []
    
    def get_top_smashers(self, limit: int = 10) -> List[Dict]:
        """Get top users by smash count"""
        try:
            results = list(
                self.users.find(
                    {"total_smash": {"$gt": 0}},
                    {
                        "user_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "display_name": 1,
                        "total_smash": 1
                    }
                )
                .sort("total_smash", -1)
                .limit(limit)
            )
            return results
        except Exception as e:
            logger.error(f"Error in get_top_smashers: {e}")
            return []
    
    def get_top_streaks(self, limit: int = 10) -> List[Dict]:
        """Get top users by daily streak"""
        try:
            results = list(
                self.users.find(
                    {"daily_streak": {"$gt": 0}},
                    {
                        "user_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "display_name": 1,
                        "daily_streak": 1
                    }
                )
                .sort("daily_streak", -1)
                .limit(limit)
            )
            return results
        except Exception as e:
            logger.error(f"Error in get_top_streaks: {e}")
            return []
    
    def get_user_rank(self, user_id: int, leaderboard_type: str = "collection") -> int:
        """Get user's rank in a specific leaderboard"""
        try:
            if leaderboard_type == "collection":
                pipeline = [
                    {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                results = list(self.collections.aggregate(pipeline))
                for i, r in enumerate(results, 1):
                    if r["_id"] == user_id:
                        return i
                        
            elif leaderboard_type == "coins":
                pipeline = [
                    {"$match": {"coins": {"$gt": 0}}},
                    {"$sort": {"coins": -1}},
                    {"$group": {
                        "_id": None,
                        "users": {"$push": "$user_id"}
                    }}
                ]
                results = list(self.users.aggregate(pipeline))
                if results:
                    users = results[0].get("users", [])
                    if user_id in users:
                        return users.index(user_id) + 1
                        
            elif leaderboard_type == "wins":
                pipeline = [
                    {"$match": {"total_wins": {"$gt": 0}}},
                    {"$sort": {"total_wins": -1}},
                    {"$group": {
                        "_id": None,
                        "users": {"$push": "$user_id"}
                    }}
                ]
                results = list(self.users.aggregate(pipeline))
                if results:
                    users = results[0].get("users", [])
                    if user_id in users:
                        return users.index(user_id) + 1
            
            return 0
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════════════
    #  TRADE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def create_trade(self, from_user: int, to_user: int, waifu_id: int, 
                     waifu_name: str, coins: int = 0, waifu_image: str = None) -> str:
        """Create a trade request"""
        trade_data = {
            "from_user": from_user,
            "to_user": to_user,
            "waifu_id": waifu_id,
            "waifu_name": waifu_name,
            "waifu_image": waifu_image,
            "coins": coins,
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5)
        }
        result = self.trades.insert_one(trade_data)
        return str(result.inserted_id)
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get trade by ID"""
        from bson import ObjectId
        try:
            return self.trades.find_one({"_id": ObjectId(trade_id)})
        except:
            return None
    
    def get_pending_trades(self, user_id: int) -> List[Dict]:
        """Get pending trades for user"""
        return list(self.trades.find({
            "to_user": user_id,
            "status": "pending",
            "expires_at": {"$gt": datetime.now()}
        }))
    
    def get_outgoing_trades(self, user_id: int) -> List[Dict]:
        """Get outgoing trades from user"""
        return list(self.trades.find({
            "from_user": user_id,
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
            # Remove from sender
            if trade.get("waifu_image"):
                self.remove_from_collection_by_image(
                    trade["from_user"], 
                    trade["waifu_id"],
                    trade["waifu_image"]
                )
            else:
                self.remove_from_collection(trade["from_user"], trade["waifu_id"])
            
            # Add to receiver
            new_waifu = {
                "id": waifu.get("waifu_id"),
                "name": waifu.get("waifu_name"),
                "anime": waifu.get("waifu_anime"),
                "rarity": waifu.get("waifu_rarity"),
                "image": waifu.get("waifu_image"),
                "obtained_method": "trade"
            }
            self.add_to_collection(trade["to_user"], new_waifu)
        
        # Handle coins
        if trade.get("coins", 0) > 0:
            self.add_coins(trade["from_user"], trade["coins"])
            self.remove_coins(trade["to_user"], trade["coins"])
        
        self.trades.update_one(
            {"_id": ObjectId(trade_id)},
            {"$set": {"status": "accepted", "completed_at": datetime.now()}}
        )
        return True
    
    def reject_trade(self, trade_id: str) -> bool:
        """Reject a trade"""
        from bson import ObjectId
        
        try:
            result = self.trades.update_one(
                {"_id": ObjectId(trade_id)},
                {"$set": {"status": "rejected", "completed_at": datetime.now()}}
            )
            return result.modified_count > 0
        except:
            return False
    
    def cancel_trade(self, trade_id: str, user_id: int) -> bool:
        """Cancel a trade (by sender)"""
        from bson import ObjectId
        
        try:
            result = self.trades.update_one(
                {
                    "_id": ObjectId(trade_id),
                    "from_user": user_id,
                    "status": "pending"
                },
                {"$set": {"status": "cancelled", "completed_at": datetime.now()}}
            )
            return result.modified_count > 0
        except:
            return False
    
    def cleanup_expired_trades(self) -> int:
        """Clean up expired trades"""
        try:
            result = self.trades.update_many(
                {
                    "status": "pending",
                    "expires_at": {"$lt": datetime.now()}
                },
                {"$set": {"status": "expired"}}
            )
            return result.modified_count
        except Exception as e:
            logger.error(f"Error cleaning up expired trades: {e}")
            return 0
    
    def get_trade_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's trade history"""
        try:
            return list(self.trades.find({
                "$or": [
                    {"from_user": user_id},
                    {"to_user": user_id}
                ]
            }).sort("created_at", -1).limit(limit))
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    #  INVENTORY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def add_to_inventory(self, user_id: int, item: Dict) -> bool:
        """Add item to user inventory"""
        try:
            item["added_at"] = datetime.now()
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
    
    def clear_inventory(self, user_id: int) -> bool:
        """Clear user's inventory"""
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": {"inventory": []}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error clearing inventory: {e}")
            return False
    
    def get_inventory_item(self, user_id: int, item_id: str) -> Optional[Dict]:
        """Get specific item from inventory"""
        inventory = self.get_inventory(user_id)
        for item in inventory:
            if item.get("id") == item_id:
                return item
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    #  GLOBAL STATS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_global_stats(self) -> Dict:
        """Get global bot statistics"""
        try:
            total_users = self.users.count_documents({})
            total_groups = self.groups.count_documents({})
            total_waifus = self.collections.count_documents({})
            
            smash_result = list(self.users.aggregate([
                {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$total_smash", 0]}}}}
            ]))
            
            pass_result = list(self.users.aggregate([
                {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$total_pass", 0]}}}}
            ]))
            
            coins_result = list(self.users.aggregate([
                {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$coins", 0]}}}}
            ]))
            
            stats = {
                "total_users": total_users,
                "total_groups": total_groups,
                "total_waifus_collected": total_waifus,
                "total_smashes": smash_result[0]["total"] if smash_result else 0,
                "total_passes": pass_result[0]["total"] if pass_result else 0,
                "total_coins": coins_result[0]["total"] if coins_result else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {
                "total_users": 0,
                "total_groups": 0,
                "total_waifus_collected": 0,
                "total_smashes": 0,
                "total_passes": 0,
                "total_coins": 0
            }
    
    def increment_global_stat(self, stat_name: str, value: int = 1) -> bool:
        """Increment a global stat"""
        try:
            result = self.stats.update_one(
                {"name": "global"},
                {"$inc": {stat_name: value}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error incrementing global stat: {e}")
            return False
    
    def get_bot_uptime_stats(self) -> Dict:
        """Get bot uptime/activity stats"""
        try:
            now = datetime.now()
            
            # Active in last hour
            hour_ago = now - timedelta(hours=1)
            active_hour = self.users.count_documents({"last_active": {"$gte": hour_ago}})
            
            # Active in last 24 hours
            day_ago = now - timedelta(hours=24)
            active_day = self.users.count_documents({"last_active": {"$gte": day_ago}})
            
            # Active in last 7 days
            week_ago = now - timedelta(days=7)
            active_week = self.users.count_documents({"last_active": {"$gte": week_ago}})
            
            # New users today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            new_today = self.users.count_documents({"created_at": {"$gte": today_start}})
            
            return {
                "active_last_hour": active_hour,
                "active_last_24h": active_day,
                "active_last_7d": active_week,
                "new_users_today": new_today
            }
        except Exception as e:
            logger.error(f"Error getting uptime stats: {e}")
            return {
                "active_last_hour": 0,
                "active_last_24h": 0,
                "active_last_7d": 0,
                "new_users_today": 0
            }
    
    # ═══════════════════════════════════════════════════════════════════
    #  DEBUG & MAINTENANCE METHODS
    # ═══════════════════════════════════════════════════════════════════
    
    def debug_check_data(self) -> Dict:
        """Debug method to check database state"""
        try:
            users_count = self.users.count_documents({})
            groups_count = self.groups.count_documents({})
            collections_count = self.collections.count_documents({})
            trades_count = self.trades.count_documents({})
            waifus_count = self.waifus.count_documents({})
            
            sample_user = self.users.find_one({})
            sample_collection = self.collections.find_one({})
            sample_group = self.groups.find_one({})
            
            users_with_coins = self.users.count_documents({"coins": {"$gt": 0}})
            users_with_wins = self.users.count_documents({"total_wins": {"$gt": 0}})
            banned_users = self.users.count_documents({"banned": True})
            
            return {
                "users_count": users_count,
                "groups_count": groups_count,
                "collections_count": collections_count,
                "trades_count": trades_count,
                "waifus_registry_count": waifus_count,
                "sample_user": sample_user,
                "sample_collection": sample_collection,
                "sample_group": sample_group,
                "users_with_coins": users_with_coins,
                "users_with_wins": users_with_wins,
                "banned_users": banned_users
            }
        except Exception as e:
            logger.error(f"Error in debug check: {e}")
            return {"error": str(e)}
    
    def vacuum_database(self) -> Dict:
        """Clean up old/unnecessary data"""
        try:
            results = {}
            
            # Clean expired trades
            expired_trades = self.cleanup_expired_trades()
            results["expired_trades_cleaned"] = expired_trades
            
            # Clean invalid waifus
            invalid_waifus = self.cleanup_invalid_waifus()
            results["invalid_waifus_cleaned"] = invalid_waifus
            
            # Clean old cooldowns (should auto-expire, but just in case)
            old_cooldowns = self.cooldowns.delete_many({
                "expires_at": {"$lt": datetime.now() - timedelta(days=1)}
            })
            results["old_cooldowns_cleaned"] = old_cooldowns.deleted_count
            
            logger.info(f"Database vacuum completed: {results}")
            return results
        except Exception as e:
            logger.error(f"Error during vacuum: {e}")
            return {"error": str(e)}
    
    def get_database_size(self) -> Dict:
        """Get size of each collection"""
        try:
            stats = {}
            for collection_name in ["users", "collections", "trades", "cooldowns", "waifus", "groups", "stats"]:
                collection = self.db[collection_name]
                stats[collection_name] = {
                    "count": collection.count_documents({}),
                    "size": self.db.command("collstats", collection_name).get("size", 0)
                }
            return stats
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return {"error": str(e)}
    
    def backup_user_data(self, user_id: int) -> Dict:
        """Export all user data for backup"""
        try:
            user = self.get_user(user_id)
            collection = self.get_full_collection(user_id)
            trades = self.get_trade_history(user_id, limit=100)
            
            return {
                "user": user,
                "collection": collection,
                "trades": trades,
                "exported_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error backing up user data: {e}")
            return {"error": str(e)}

def mark_group_inactive(self, chat_id: int):
    """Mark a group as inactive (bot removed)"""
    try:
        self.groups.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "is_active": False,
                    "left_at": datetime.now()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error marking group inactive: {e}")

def update_group_member_count(self, chat_id: int, count: int):
    """Update group member count"""
    try:
        self.groups.update_one(
            {"chat_id": chat_id},
            {"$set": {"member_count": count, "last_updated": datetime.now()}}
        )
    except Exception as e:
        logger.error(f"Error updating member count: {e}")

def update_group_info(self, chat_id: int, title: str = None, username: str = None, member_count: int = None):
    """Update group information"""
    try:
        update_data = {"last_updated": datetime.now(), "is_active": True}
        
        if title:
            update_data["title"] = title
        if username:
            update_data["username"] = username
        if member_count:
            update_data["member_count"] = member_count
            
        self.groups.update_one(
            {"chat_id": chat_id},
            {"$set": update_data}
        )
    except Exception as e:
        logger.error(f"Error updating group info: {e}")

def get_active_groups_count(self, hours: int = 24) -> int:
    """Get count of active groups in last X hours"""
    try:
        cutoff = datetime.now() - timedelta(hours=hours)
        return self.groups.count_documents({
            "last_active": {"$gte": cutoff},
            "is_active": {"$ne": False}
        })
    except Exception as e:
        logger.error(f"Error getting active groups: {e}")
        return 0

def update_user_activity(self, user_id: int):
    """Update user's last active timestamp"""
    try:
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.now()}}
        )
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

# Create global instance
db = Database()
