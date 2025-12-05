# database/mongo.py - MongoDB Operations

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import config


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
        
        # Create indexes for faster queries
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimization"""
        self.users.create_index("user_id", unique=True)
        self.collections.create_index("user_id")
        self.collections.create_index([("user_id", 1), ("waifu_id", 1)])
        self.cooldowns.create_index("user_id")
        self.stats.create_index("user_id", unique=True)
    
    # ============ USER OPERATIONS ============
    
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
            "collection": [],
            "inventory": [],
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
                self.save_user_info_data(user_id, username, first_name)
        return user
    
    def save_user_info(self, user) -> bool:
        """Save user's Telegram info to database"""
        if not user:
            return False
        
        try:
            update_data = {"user_id": user.id}
            
            if hasattr(user, 'first_name') and user.first_name:
                update_data["first_name"] = user.first_name
            if hasattr(user, 'last_name') and user.last_name:
                update_data["last_name"] = user.last_name
            if hasattr(user, 'username') and user.username:
                update_data["username"] = user.username
            
            self.users.update_one(
                {"user_id": user.id},
                {
                    "$set": update_data,
                    "$setOnInsert": {
                        "coins": 0,
                        "total_smash": 0,
                        "total_pass": 0,
                        "total_wins": 0,
                        "total_losses": 0,
                        "total_earned": 0,
                        "total_spent": 0,
                        "collection": [],
                        "inventory": [],
                        "created_at": datetime.now(),
                        "last_daily": None
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving user info: {e}")
            return False
    
    def save_user_info_data(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Save user info from raw data"""
        try:
            update_data = {}
            if first_name:
                update_data["first_name"] = first_name
            if last_name:
                update_data["last_name"] = last_name
            if username:
                update_data["username"] = username
            
            if update_data:
                self.users.update_one(
                    {"user_id": user_id},
                    {"$set": update_data},
                    upsert=True
                )
            return True
        except Exception as e:
            print(f"Error saving user data: {e}")
            return False
    
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
    
    # ============ COIN OPERATIONS ============
    
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
    
    def update_coins(self, user_id: int, amount: int) -> bool:
        """
        Update coins (add or remove based on positive/negative value)
        
        Args:
            user_id: User ID
            amount: Positive to add, negative to remove
        
        Returns:
            bool: True if successful
        """
        if amount >= 0:
            # Adding coins
            result = self.users.update_one(
                {"user_id": user_id},
                {"$inc": {"coins": amount, "total_earned": amount}},
                upsert=True
            )
        else:
            # Removing coins - check balance first
            user = self.get_user(user_id)
            current_coins = user.get("coins", 0) if user else 0
            
            if current_coins >= abs(amount):
                result = self.users.update_one(
                    {"user_id": user_id},
                    {"$inc": {"coins": amount, "total_spent": abs(amount)}},
                    upsert=True
                )
            else:
                return False
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    def get_coins(self, user_id: int) -> int:
        """Get user's coin balance"""
        user = self.get_user(user_id)
        return user.get("coins", 0) if user else 0
    
    # ============ COLLECTION OPERATIONS ============
    
    def add_waifu_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """Add waifu to user collection (in collections table)"""
        collection_entry = {
            "user_id": user_id,
            "waifu_id": waifu_data.get("id"),
            "waifu_name": waifu_data.get("name"),
            "waifu_anime": waifu_data.get("anime"),
            "waifu_rarity": waifu_data.get("rarity"),
            "waifu_image": waifu_data.get("image"),
            "waifu_power": waifu_data.get("power", 0),
            "obtained_at": datetime.now(),
            "obtained_method": waifu_data.get("obtained_from", "smash")
        }
        self.collections.insert_one(collection_entry)
        return True
    
    def add_to_collection(self, user_id: int, waifu_data: Dict) -> bool:
        """
        Alias for add_waifu_to_collection
        Also adds to user's embedded collection array
        """
        # Add to collections table
        self.add_waifu_to_collection(user_id, waifu_data)
        
        # Also add to user's embedded collection (optional, for quick access)
        waifu_entry = {
            "id": waifu_data.get("id"),
            "name": waifu_data.get("name"),
            "anime": waifu_data.get("anime"),
            "rarity": waifu_data.get("rarity"),
            "image": waifu_data.get("image"),
            "power": waifu_data.get("power", 0),
            "obtained_at": waifu_data.get("obtained_at", datetime.now().strftime("%Y-%m-%d %H:%M")),
            "obtained_from": waifu_data.get("obtained_from", "smash")
        }
        
        self.users.update_one(
            {"user_id": user_id},
            {"$push": {"collection": waifu_entry}},
            upsert=True
        )
        return True
    
    def remove_from_collection(self, user_id: int, waifu_id: int) -> bool:
        """
        Remove waifu from collection
        Removes from both collections table and user's embedded array
        """
        # Remove from collections table
        self.collections.delete_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
        
        # Remove from user's embedded collection
        self.users.update_one(
            {"user_id": user_id},
            {"$pull": {"collection": {"id": waifu_id}}}
        )
        return True
    
    def get_user_collection(self, user_id: int, page: int = 1, per_page: int = 10) -> List[Dict]:
        """Get user's waifu collection with pagination"""
        skip = (page - 1) * per_page
        return list(
            self.collections.find({"user_id": user_id})
            .sort("obtained_at", -1)
            .skip(skip)
            .limit(per_page)
        )
    
    def get_full_collection(self, user_id: int) -> List[Dict]:
        """Get user's complete collection without pagination"""
        return list(self.collections.find({"user_id": user_id}).sort("obtained_at", -1))
    
    def get_collection_count(self, user_id: int) -> int:
        """Get total waifus in user collection"""
        return self.collections.count_documents({"user_id": user_id})
    
    def check_waifu_owned(self, user_id: int, waifu_id: int) -> bool:
        """Check if user owns a specific waifu"""
        return self.collections.find_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        }) is not None
    
    def get_waifu_from_collection(self, user_id: int, waifu_id: int) -> Optional[Dict]:
        """Get specific waifu from user collection"""
        return self.collections.find_one({
            "user_id": user_id,
            "waifu_id": waifu_id
        })
    
    def remove_waifu_from_collection(self, user_id: int, waifu_id: int) -> bool:
        """Remove waifu from collection (for trading)"""
        return self.remove_from_collection(user_id, waifu_id)
    
    def get_user_collection_by_rarity(self, user_id: int, rarity: str) -> List[Dict]:
        """Get user waifus filtered by rarity"""
        return list(self.collections.find({
            "user_id": user_id,
            "waifu_rarity": rarity
        }))
    
    def get_duplicate_waifus(self, user_id: int) -> List[Dict]:
        """Get duplicate waifus in collection"""
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
    
    # ============ COOLDOWN OPERATIONS ============
    
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
    
    # ============ DAILY OPERATIONS ============
    
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
        self.add_coins(user_id, coins)
        self.update_user(user_id, {"last_daily": datetime.now()})
        return True
    
    # ============ LEADERBOARD OPERATIONS ============
    
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
                "first_name": None
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
    
    # ============ TRADE OPERATIONS ============
    
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
        trade = self.trades.find_one({"_id": ObjectId(trade_id)})
        
        if not trade or trade["status"] != "pending":
            return False
        
        if trade["expires_at"] < datetime.now():
            return False
        
        # Transfer waifu
        waifu = self.get_waifu_from_collection(trade["from_user"], trade["waifu_id"])
        if waifu:
            self.remove_from_collection(trade["from_user"], trade["waifu_id"])
            waifu["user_id"] = trade["to_user"]
            waifu["obtained_method"] = "trade"
            waifu["obtained_at"] = datetime.now()
            if "_id" in waifu:
                del waifu["_id"]
            self.collections.insert_one(waifu)
        
        # Handle coins if any
        if trade["coins"] > 0:
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
        result = self.trades.update_one(
            {"_id": ObjectId(trade_id)},
            {"$set": {"status": "rejected"}}
        )
        return result.modified_count > 0
    
    # ============ GLOBAL STATS ============
    
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


# Create global instance
db = Database()
