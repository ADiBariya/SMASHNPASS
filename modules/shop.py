from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from helpers.utils import load_waifus, get_rarity_emoji, get_rarity_value
from config import COMMAND_PREFIX
from datetime import datetime
import random
import asyncio

__MODULE__ = "Shop"
__HELP__ = """
🏪 **Shop Commands**

`.shop` - Open waifu shop
`.buy <item>` - Buy an item
`.balance` - Check your coins
`.sell <waifu_id>` - Sell a waifu
`.inventory` - View your items

**Available Items:**
📦 Common Box - 100 coins
💎 Rare Box - 500 coins
🎁 Epic Box - 1500 coins
👑 Legendary Box - 5000 coins
"""

# Shop items configuration
SHOP_ITEMS = {
    "common_box": {
        "name": "Common Box",
        "price": 100,
        "emoji": "📦",
        "description": "Contains Common/Uncommon waifus",
        "rarities": ["Common", "Uncommon"],
        "weights": [70, 30]
    },
    "rare_box": {
        "name": "Rare Box",
        "price": 500,
        "emoji": "💎",
        "description": "Contains Uncommon/Rare waifus",
        "rarities": ["Uncommon", "Rare"],
        "weights": [40, 60]
    },
    "epic_box": {
        "name": "Epic Box",
        "price": 1500,
        "emoji": "🎁",
        "description": "Contains Rare/Epic waifus",
        "rarities": ["Rare", "Epic"],
        "weights": [50, 50]
    },
    "legendary_box": {
        "name": "Legendary Box",
        "price": 5000,
        "emoji": "👑",
        "description": "Contains Epic/Legendary waifus",
        "rarities": ["Epic", "Legendary"],
        "weights": [60, 40]
    },
    "premium_box": {
        "name": "Premium Box",
        "price": 10000,
        "emoji": "🌟",
        "description": "Guaranteed Legendary waifu!",
        "rarities": ["Legendary"],
        "weights": [100]
    }
}

# Special items
SPECIAL_ITEMS = {
    "coin_boost": {
        "name": "Coin Boost",
        "price": 2000,
        "emoji": "💰",
        "description": "2x coins for 1 hour",
        "duration": 3600
    },
    "luck_charm": {
        "name": "Luck Charm",
        "price": 3000,
        "emoji": "🍀",
        "description": "+20% win chance for 1 hour",
        "duration": 3600
    }
}


@Client.on_message(filters.command(["shop", "store", "market"], prefixes=COMMAND_PREFIX))
async def shop_cmd(client: Client, message: Message):
    """Open the shop"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    coins = user_data.get("coins", 0)
    
    text = f"""
🏪 **WAIFU SHOP**

💰 **Your Balance:** {coins:,} coins

━━━━━━━━━━━━━━━━━━━━
📦 **LOOT BOXES**
━━━━━━━━━━━━━━━━━━━━
"""
    
    for item_id, item in SHOP_ITEMS.items():
        can_afford = "✅" if coins >= item["price"] else "❌"
        text += f"\n{item['emoji']} **{item['name']}** - {item['price']:,} coins {can_afford}"
        text += f"\n   └ {item['description']}"
    
    text += "\n\n━━━━━━━━━━━━━━━━━━━━"
    text += "\n🎯 **SPECIAL ITEMS**"
    text += "\n━━━━━━━━━━━━━━━━━━━━"
    
    for item_id, item in SPECIAL_ITEMS.items():
        can_afford = "✅" if coins >= item["price"] else "❌"
        text += f"\n{item['emoji']} **{item['name']}** - {item['price']:,} coins {can_afford}"
        text += f"\n   └ {item['description']}"
    
    # Create buttons
    buttons = [
        [
            InlineKeyboardButton("📦 Common (100)", callback_data="shop_buy_common_box"),
            InlineKeyboardButton("💎 Rare (500)", callback_data="shop_buy_rare_box")
        ],
        [
            InlineKeyboardButton("🎁 Epic (1.5k)", callback_data="shop_buy_epic_box"),
            InlineKeyboardButton("👑 Legend (5k)", callback_data="shop_buy_legendary_box")
        ],
        [
            InlineKeyboardButton("🌟 Premium (10k)", callback_data="shop_buy_premium_box")
        ],
        [
            InlineKeyboardButton("💰 Coin Boost", callback_data="shop_buy_coin_boost"),
            InlineKeyboardButton("🍀 Luck Charm", callback_data="shop_buy_luck_charm")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"),
            InlineKeyboardButton("📦 Inventory", callback_data="shop_inventory")
        ]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^shop_buy_(.+)$"))
async def shop_buy_callback(client: Client, callback: CallbackQuery):
    """Handle shop purchases"""
    user_id = callback.from_user.id
    item_id = callback.matches[0].group(1)
    
    # Check if it's a box or special item
    if item_id in SHOP_ITEMS:
        item = SHOP_ITEMS[item_id]
        is_box = True
    elif item_id in SPECIAL_ITEMS:
        item = SPECIAL_ITEMS[item_id]
        is_box = False
    else:
        return await callback.answer("❌ Item not found!", show_alert=True)
    
    # Check balance
    user_data = await db.get_user(user_id)
    coins = user_data.get("coins", 0)
    
    if coins < item["price"]:
        return await callback.answer(
            f"❌ Not enough coins!\n\nYou need: {item['price']:,}\nYou have: {coins:,}",
            show_alert=True
        )
    
    if is_box:
        # Open loot box
        await open_loot_box(callback, item_id, item)
    else:
        # Buy special item
        await buy_special_item(callback, item_id, item)


async def open_loot_box(callback: CallbackQuery, item_id: str, item: dict):
    """Open a loot box and give waifu"""
    user_id = callback.from_user.id
    
    # Deduct coins
    await db.update_coins(user_id, -item["price"])
    
    # Show opening animation
    await callback.message.edit_text(
        f"{item['emoji']} **Opening {item['name']}...**\n\n"
        f"🎰 Rolling..."
    )
    
    await asyncio.sleep(1)
    
    # Select rarity
    selected_rarity = random.choices(
        item["rarities"],
        weights=item["weights"]
    )[0]
    
    # Get waifu of that rarity
    waifus = load_waifus()
    rarity_waifus = [w for w in waifus if w.get("rarity") == selected_rarity]
    
    if not rarity_waifus:
        rarity_waifus = waifus
    
    waifu = random.choice(rarity_waifus)
    
    # Add to collection
    waifu_copy = waifu.copy()
    waifu_copy["obtained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    waifu_copy["obtained_from"] = f"shop_{item_id}"
    
    await db.add_to_collection(user_id, waifu_copy)
    
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    value = get_rarity_value(waifu.get("rarity", "Common"))
    
    text = f"""
🎉 **{item['name']} OPENED!**

━━━━━━━━━━━━━━━━━━━━
{emoji} **{waifu['name']}**
━━━━━━━━━━━━━━━━━━━━

📺 **Anime:** {waifu.get('anime', 'Unknown')}
⭐ **Rarity:** {waifu.get('rarity', 'Common')}
💰 **Value:** {value:,} coins

✅ Added to your collection!
"""
    
    buttons = [
        [
            InlineKeyboardButton("🎰 Open Another", callback_data=f"shop_buy_{item_id}"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="shop_refresh")
        ]
    ]
    
    if waifu.get("image"):
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=waifu["image"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    await callback.answer(f"🎉 You got {waifu['name']}!")


async def buy_special_item(callback: CallbackQuery, item_id: str, item: dict):
    """Buy a special item"""
    user_id = callback.from_user.id
    
    # Deduct coins
    await db.update_coins(user_id, -item["price"])
    
    # Add item to inventory
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$push": {
                "inventory": {
                    "item_id": item_id,
                    "name": item["name"],
                    "emoji": item["emoji"],
                    "purchased_at": datetime.now().isoformat(),
                    "used": False
                }
            }
        }
    )
    
    text = f"""
✅ **Purchase Successful!**

{item['emoji']} **{item['name']}**
💰 Paid: {item['price']:,} coins

📦 Item added to your inventory!
Use `.inventory` to view and activate.
"""
    
    buttons = [
        [
            InlineKeyboardButton("📦 Inventory", callback_data="shop_inventory"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="shop_refresh")
        ]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer("✅ Purchased!")


@Client.on_callback_query(filters.regex("^shop_refresh$"))
async def shop_refresh_callback(client: Client, callback: CallbackQuery):
    """Refresh shop"""
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    coins = user_data.get("coins", 0)
    
    text = f"""
🏪 **WAIFU SHOP**

💰 **Your Balance:** {coins:,} coins

━━━━━━━━━━━━━━━━━━━━
📦 **LOOT BOXES**
━━━━━━━━━━━━━━━━━━━━
"""
    
    for item_id, item in SHOP_ITEMS.items():
        can_afford = "✅" if coins >= item["price"] else "❌"
        text += f"\n{item['emoji']} **{item['name']}** - {item['price']:,} coins {can_afford}"
    
    buttons = [
        [
            InlineKeyboardButton("📦 Common (100)", callback_data="shop_buy_common_box"),
            InlineKeyboardButton("💎 Rare (500)", callback_data="shop_buy_rare_box")
        ],
        [
            InlineKeyboardButton("🎁 Epic (1.5k)", callback_data="shop_buy_epic_box"),
            InlineKeyboardButton("👑 Legend (5k)", callback_data="shop_buy_legendary_box")
        ],
        [
            InlineKeyboardButton("🌟 Premium (10k)", callback_data="shop_buy_premium_box")
        ]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer("🔄 Refreshed!")


@Client.on_callback_query(filters.regex("^shop_inventory$"))
async def shop_inventory_callback(client: Client, callback: CallbackQuery):
    """View inventory"""
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    inventory = user_data.get("inventory", [])
    
    unused_items = [i for i in inventory if not i.get("used", False)]
    
    if not unused_items:
        text = "📦 **Your Inventory**\n\n📭 Empty! Buy items from the shop."
    else:
        text = "📦 **Your Inventory**\n\n"
        for i, item in enumerate(unused_items):
            text += f"{item['emoji']} **{item['name']}**\n"
    
    buttons = [[InlineKeyboardButton("🔙 Back to Shop", callback_data="shop_refresh")]]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await callback.answer()


@Client.on_message(filters.command(["balance", "bal", "coins", "wallet"], prefixes=COMMAND_PREFIX))
async def balance_cmd(client: Client, message: Message):
    """Check coin balance"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    coins = user_data.get("coins", 0)
    total_earned = user_data.get("total_earned", 0)
    total_spent = user_data.get("total_spent", 0)
    
    text = f"""
💰 **Your Wallet**

━━━━━━━━━━━━━━━━━━━━
💵 **Balance:** {coins:,} coins
━━━━━━━━━━━━━━━━━━━━

📈 **Total Earned:** {total_earned:,}
📉 **Total Spent:** {total_spent:,}
"""
    
    buttons = [
        [
            InlineKeyboardButton("🏪 Shop", callback_data="shop_refresh"),
            InlineKeyboardButton("📅 Daily", callback_data="claim_daily")
        ]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command(["buy", "purchase"], prefixes=COMMAND_PREFIX))
async def buy_cmd(client: Client, message: Message):
    """Quick buy command"""
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:** `.buy <item_name>`\n\n"
            "**Available items:**\n"
            "• `common_box` - 100 coins\n"
            "• `rare_box` - 500 coins\n"
            "• `epic_box` - 1500 coins\n"
            "• `legendary_box` - 5000 coins\n"
            "• `premium_box` - 10000 coins"
        )
    
    item_id = message.command[1].lower().replace(" ", "_")
    
    # Normalize item names
    item_aliases = {
        "common": "common_box",
        "rare": "rare_box",
        "epic": "epic_box",
        "legendary": "legendary_box",
        "legend": "legendary_box",
        "premium": "premium_box"
    }
    
    item_id = item_aliases.get(item_id, item_id)
    
    if item_id not in SHOP_ITEMS and item_id not in SPECIAL_ITEMS:
        return await message.reply_text("❌ Item not found! Use `.shop` to see available items.")
    
    # Check balance
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    coins = user_data.get("coins", 0)
    
    item = SHOP_ITEMS.get(item_id) or SPECIAL_ITEMS.get(item_id)
    
    if coins < item["price"]:
        return await message.reply_text(
            f"❌ **Not enough coins!**\n\n"
            f"**Item:** {item['name']}\n"
            f"**Price:** {item['price']:,}\n"
            f"**Your balance:** {coins:,}\n"
            f"**Need:** {item['price'] - coins:,} more"
        )
    
    # Confirm purchase
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"shop_buy_{item_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="shop_refresh")
        ]
    ]
    
    await message.reply_text(
        f"🛒 **Confirm Purchase**\n\n"
        f"{item['emoji']} **{item['name']}**\n"
        f"💰 Price: {item['price']:,} coins\n\n"
        f"Your balance: {coins:,} coins\n"
        f"After purchase: {coins - item['price']:,} coins",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_message(filters.command(["inventory", "inv", "items"], prefixes=COMMAND_PREFIX))
async def inventory_cmd(client: Client, message: Message):
    """View inventory"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    inventory = user_data.get("inventory", [])
    
    unused_items = [i for i in inventory if not i.get("used", False)]
    
    if not unused_items:
        return await message.reply_text(
            "📦 **Your Inventory**\n\n"
            "📭 Empty!\n\n"
            "Use `.shop` to buy items."
        )
    
    text = "📦 **Your Inventory**\n\n"
    
    for i, item in enumerate(unused_items, 1):
        text += f"**{i}.** {item['emoji']} {item['name']}\n"
    
    text += f"\n📊 **Total Items:** {len(unused_items)}"
    
    await message.reply_text(text)


@Client.on_message(filters.command(["sell", "sellwaifu"], prefixes=COMMAND_PREFIX))
async def sell_cmd(client: Client, message: Message):
    """Sell a waifu"""
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `.sell <waifu_id>`")
    
    try:
        waifu_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid waifu ID!")
    
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    # Find waifu
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await message.reply_text("❌ You don't own this waifu!")
    
    # Calculate sell price (50% of value)
    value = get_rarity_value(waifu.get("rarity", "Common"))
    sell_price = value // 2
    
    buttons = [
        [
            InlineKeyboardButton("✅ Sell", callback_data=f"confirm_sell_{waifu_id}_{sell_price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        ]
    ]
    
    emoji = get_rarity_emoji(waifu.get("rarity", "Common"))
    
    await message.reply_text(
        f"💰 **Sell Waifu?**\n\n"
        f"{emoji} **{waifu['name']}**\n"
        f"📺 {waifu.get('anime', 'Unknown')}\n"
        f"⭐ {waifu.get('rarity', 'Common')}\n\n"
        f"💵 **Value:** {value:,} coins\n"
        f"💰 **Sell Price:** {sell_price:,} coins (50%)\n\n"
        f"⚠️ This cannot be undone!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^confirm_sell_(\d+)_(\d+)$"))
async def confirm_sell_callback(client: Client, callback: CallbackQuery):
    """Confirm waifu sale"""
    user_id = callback.from_user.id
    waifu_id = int(callback.matches[0].group(1))
    sell_price = int(callback.matches[0].group(2))
    
    # Check ownership
    user_data = await db.get_user(user_id)
    collection = user_data.get("collection", [])
    
    waifu = None
    for w in collection:
        if w.get("id") == waifu_id:
            waifu = w
            break
    
    if not waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)
    
    # Remove and add coins
    await db.remove_from_collection(user_id, waifu_id)
    await db.update_coins(user_id, sell_price)
    
    # Track spending
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"total_earned": sell_price}}
    )
    
    await callback.message.edit_text(
        f"✅ **Waifu Sold!**\n\n"
        f"**Sold:** {waifu['name']}\n"
        f"**Received:** {sell_price:,} coins\n\n"
        f"💰 Coins added to your balance!"
    )
    await callback.answer("✅ Sold!")


@Client.on_callback_query(filters.regex("^cancel_action$"))
async def cancel_action_callback(client: Client, callback: CallbackQuery):
    """Cancel any action"""
    await callback.message.edit_text("❌ Action cancelled.")
    await callback.answer()