# modules/shop.py - Shop System (FIXED - Original Prices + Custom Rarity)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from helpers.utils import load_waifus, get_rarity_emoji
from config import COMMAND_PREFIX
from datetime import datetime
import random
import asyncio
import inspect

__MODULE__ = "Shop"
__HELP__ = """
🏪 **Shop Commands**

`.shop` - Open waifu shop
`.buy <item>` - Buy an item
`.balance` - Check your coins
`.sell <waifu_id>` - Sell a waifu
`.inventory` - View your items

**Rarity Order (Low → High):**
⚪ Common < 🟣 Epic < 🟡 Legendary < 🔵 Rare

**Available Boxes:**
📦 Common Box - 100 coins
🟣 Epic Box - 500 coins
🟡 Legendary Box - 1,500 coins
💎 Rare Box - 5,000 coins (Best!)
🌟 Premium Box - 10,000 coins (Guaranteed Rare!)
"""

# Rarity points system (for sell value) - YOUR ORDER
RARITY_POINTS = {
    "common": 10,
    "epic": 25,
    "legendary": 50,
    "rare": 100
}

# Shop items - ORIGINAL PRICES with YOUR RARITY ORDER
SHOP_ITEMS = {
    "common_box": {
        "name": "Common Box",
        "price": 100,
        "emoji": "📦",
        "description": "Contains ⚪ Common waifu",
        "rarity": "common"
    },
    "epic_box": {
        "name": "Epic Box",
        "price": 500,
        "emoji": "🟣",
        "description": "Contains 🟣 Epic waifu",
        "rarity": "epic"
    },
    "legendary_box": {
        "name": "Legendary Box",
        "price": 1500,
        "emoji": "🟡",
        "description": "Contains 🟡 Legendary waifu",
        "rarity": "legendary"
    },
    "rare_box": {
        "name": "Rare Box",
        "price": 5000,
        "emoji": "💎",
        "description": "Contains 🔵 Rare waifu (Best!)",
        "rarity": "rare"
    },
    "premium_box": {
        "name": "Premium Box",
        "price": 10000,
        "emoji": "🌟",
        "description": "Guaranteed 🔵 Rare waifu!",
        "rarity": "rare"
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


def get_rarity_value(rarity: str) -> int:
    """Get coin value for rarity"""
    return RARITY_POINTS.get(rarity.lower(), 10)


# ---------- Helper to safely await sync or async DB calls ----------
async def maybe_await(value):
    """
    If `value` is awaitable/coroutine, await and return it.
    Otherwise, return value directly.
    """
    if inspect.isawaitable(value):
        return await value
    return value
# ------------------------------------------------------------------


@Client.on_message(filters.command(["shop", "store", "market"], prefixes=COMMAND_PREFIX))
async def shop_cmd(client: Client, message: Message):
    """Open the shop"""
    user_id = message.from_user.id
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, message.from_user.username, message.from_user.first_name))
    coins = user_data.get("coins", 0)

    text = f"""
🏪 **WAIFU SHOP**

💰 **Your Balance:** {coins:,} coins

━━━━━━━━━━━━━━━━━━━━
📦 **LOOT BOXES**
━━━━━━━━━━━━━━━━━━━━

**Rarity:** ⚪ Common < 🟣 Epic < 🟡 Legendary < 🔵 Rare
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

    # Buttons - ordered by rarity (low to high)
    buttons = [
        [
            InlineKeyboardButton("📦 Common (100)", callback_data="shop_buy_common_box"),
            InlineKeyboardButton("🟣 Epic (500)", callback_data="shop_buy_epic_box")
        ],
        [
            InlineKeyboardButton("🟡 Legendary (1.5k)", callback_data="shop_buy_legendary_box"),
            InlineKeyboardButton("💎 Rare (5k)", callback_data="shop_buy_rare_box")
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
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, callback.from_user.username, callback.from_user.first_name))
    coins = user_data.get("coins", 0)

    if coins < item["price"]:
        return await callback.answer(
            f"❌ Not enough coins!\n\nYou need: {item['price']:,}\nYou have: {coins:,}",
            show_alert=True
        )

    if is_box:
        await open_loot_box(callback, item_id, item)
    else:
        await buy_special_item(callback, item_id, item)


async def open_loot_box(callback: CallbackQuery, item_id: str, item: dict):
    """Open a loot box and give waifu of EXACT rarity"""
    user_id = callback.from_user.id

    # Deduct coins
    await maybe_await(db.update_coins(user_id, -item["price"]))

    # Show opening animation
    try:
        await callback.message.edit_text(
            f"{item['emoji']} **Opening {item['name']}...**\n\n"
            f"🎰 Rolling..."
        )
    except Exception:
        pass

    await asyncio.sleep(1)

    # Get the EXACT rarity from box config
    target_rarity = item.get("rarity", "common").lower()

    # Load waifus and filter by EXACT rarity
    waifus = load_waifus()
    
    # Filter waifus by exact rarity (case-insensitive match)
    rarity_waifus = [
        w for w in waifus 
        if w.get("rarity", "common").lower() == target_rarity
    ]

    print(f"🎁 [SHOP] Box: {item_id}, Target Rarity: {target_rarity}, Found: {len(rarity_waifus)} waifus")

    # If no waifus of that rarity, show error and refund
    if not rarity_waifus:
        await maybe_await(db.update_coins(user_id, item["price"]))
        
        try:
            await callback.message.edit_text(
                f"❌ **No {target_rarity.title()} waifus available!**\n\n"
                f"💰 Your coins have been refunded."
            )
        except:
            pass
        
        await callback.answer("❌ No waifus of this rarity!", show_alert=True)
        return

    # Select random waifu of that rarity
    waifu = random.choice(rarity_waifus)

    # Add to collection
    waifu_copy = waifu.copy()
    waifu_copy["obtained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    waifu_copy["obtained_from"] = f"shop_{item_id}"

    await maybe_await(db.add_to_collection(user_id, waifu_copy))

    emoji = get_rarity_emoji(waifu.get("rarity", "common"))
    value = get_rarity_value(waifu.get("rarity", "common"))
    sell_value = value // 2

    text = f"""
🎉 **{item['name']} OPENED!**

━━━━━━━━━━━━━━━━━━━━
{emoji} **{waifu['name']}**
━━━━━━━━━━━━━━━━━━━━

📺 **Anime:** {waifu.get('anime', 'Unknown')}
⭐ **Rarity:** {waifu.get('rarity', 'common').title()}
💰 **Value:** {value} coins
💵 **Sell Price:** {sell_value} coins

✅ Added to your collection!
"""

    buttons = [
        [
            InlineKeyboardButton("🎰 Open Another", callback_data=f"shop_buy_{item_id}"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="shop_refresh")
        ]
    ]

    if waifu.get("image"):
        try:
            await callback.message.delete()
        except Exception:
            pass

        try:
            await callback.message._client.send_photo(
                chat_id=callback.message.chat.id,
                photo=waifu["image"],
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            print(f"⚠️ [SHOP] Image error: {e}")
            try:
                await callback.message._client.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception:
                pass
    else:
        try:
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            try:
                await callback.message._client.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception:
                pass

    await callback.answer(f"🎉 You got {waifu['name']}!")


async def buy_special_item(callback: CallbackQuery, item_id: str, item: dict):
    """Buy a special item"""
    user_id = callback.from_user.id

    # Deduct coins
    await maybe_await(db.update_coins(user_id, -item["price"]))

    # Add item to inventory
    await maybe_await(db.users.update_one(
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
        },
        upsert=True
    ))

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

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        try:
            await callback.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass

    await callback.answer("✅ Purchased!")


@Client.on_callback_query(filters.regex("^shop_refresh$"))
async def shop_refresh_callback(client: Client, callback: CallbackQuery):
    """Refresh shop"""
    user_id = callback.from_user.id
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, callback.from_user.username, callback.from_user.first_name))
    coins = user_data.get("coins", 0)

    text = f"""
🏪 **WAIFU SHOP**

💰 **Your Balance:** {coins:,} coins

━━━━━━━━━━━━━━━━━━━━
📦 **LOOT BOXES**
━━━━━━━━━━━━━━━━━━━━

**Rarity:** ⚪ Common < 🟣 Epic < 🟡 Legendary < 🔵 Rare
"""

    for item_id, item in SHOP_ITEMS.items():
        can_afford = "✅" if coins >= item["price"] else "❌"
        text += f"\n{item['emoji']} **{item['name']}** - {item['price']:,} coins {can_afford}"
        text += f"\n   └ {item['description']}"

    buttons = [
        [
            InlineKeyboardButton("📦 Common (100)", callback_data="shop_buy_common_box"),
            InlineKeyboardButton("🟣 Epic (500)", callback_data="shop_buy_epic_box")
        ],
        [
            InlineKeyboardButton("🟡 Legendary (1.5k)", callback_data="shop_buy_legendary_box"),
            InlineKeyboardButton("💎 Rare (5k)", callback_data="shop_buy_rare_box")
        ],
        [
            InlineKeyboardButton("🌟 Premium (10k)", callback_data="shop_buy_premium_box")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"),
            InlineKeyboardButton("📦 Inventory", callback_data="shop_inventory")
        ]
    ]

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        try:
            await callback.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass

    await callback.answer("🔄 Refreshed!")


@Client.on_callback_query(filters.regex("^shop_inventory$"))
async def shop_inventory_callback(client: Client, callback: CallbackQuery):
    """View inventory"""
    user_id = callback.from_user.id
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, callback.from_user.username, callback.from_user.first_name))
    inventory = user_data.get("inventory", [])

    unused_items = [i for i in inventory if not i.get("used", False)]

    if not unused_items:
        text = "📦 **Your Inventory**\n\n📭 Empty! Buy items from the shop."
    else:
        text = "📦 **Your Inventory**\n\n"
        for i, item in enumerate(unused_items):
            text += f"{item['emoji']} **{item['name']}**\n"

    buttons = [[InlineKeyboardButton("🔙 Back to Shop", callback_data="shop_refresh")]]

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        try:
            await callback.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass

    await callback.answer()


@Client.on_message(filters.command(["balance", "bal", "coins", "wallet"], prefixes=COMMAND_PREFIX))
async def balance_cmd(client: Client, message: Message):
    """Check coin balance"""
    user_id = message.from_user.id
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, message.from_user.username, message.from_user.first_name))

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
            "**Available Boxes:**\n"
            "• `common` - 100 coins (⚪ Common)\n"
            "• `epic` - 500 coins (🟣 Epic)\n"
            "• `legendary` - 1,500 coins (🟡 Legendary)\n"
            "• `rare` - 5,000 coins (🔵 Rare - Best!)\n"
            "• `premium` - 10,000 coins (🔵 Guaranteed Rare!)"
        )

    item_id = message.command[1].lower().replace(" ", "_")

    # Normalize item names
    item_aliases = {
        "common": "common_box",
        "epic": "epic_box",
        "legendary": "legendary_box",
        "legend": "legendary_box",
        "rare": "rare_box",
        "premium": "premium_box"
    }

    item_id = item_aliases.get(item_id, item_id)

    if item_id not in SHOP_ITEMS and item_id not in SPECIAL_ITEMS:
        return await message.reply_text("❌ Item not found! Use `.shop` to see available items.")

    # Check balance
    user_id = message.from_user.id
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, message.from_user.username, message.from_user.first_name))
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
    user_data = await maybe_await(db.get_user(user_id))
    if not user_data:
        user_data = await maybe_await(db.get_or_create_user(user_id, message.from_user.username, message.from_user.first_name))
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
        return await message.reply_text(
            "❌ **Usage:** `.sell <waifu_id>`\n\n"
            "**Sell Values (50% of value):**\n"
            "• ⚪ Common (10) → 5 coins\n"
            "• 🟣 Epic (25) → 12 coins\n"
            "• 🟡 Legendary (50) → 25 coins\n"
            "• 🔵 Rare (100) → 50 coins"
        )

    try:
        waifu_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid waifu ID!")

    user_id = message.from_user.id
    
    # Get collection
    collection = await maybe_await(db.get_full_collection(user_id))
    
    if not collection:
        return await message.reply_text("❌ Your collection is empty!")

    # Find waifu
    waifu = None
    for w in collection:
        w_id = w.get("waifu_id") or w.get("id")
        try:
            if int(w_id) == waifu_id:
                waifu = w
                break
        except:
            continue

    if not waifu:
        return await message.reply_text("❌ You don't own this waifu!")

    # Calculate sell price (50% of value)
    rarity = (waifu.get("waifu_rarity") or waifu.get("rarity", "common")).lower()
    value = get_rarity_value(rarity)
    sell_price = value // 2

    buttons = [
        [
            InlineKeyboardButton("✅ Sell", callback_data=f"confirm_sell_{waifu_id}_{sell_price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        ]
    ]

    emoji = get_rarity_emoji(rarity)
    name = waifu.get("waifu_name") or waifu.get("name", "Unknown")
    anime = waifu.get("waifu_anime") or waifu.get("anime", "Unknown")

    await message.reply_text(
        f"💰 **Sell Waifu?**\n\n"
        f"{emoji} **{name}**\n"
        f"📺 {anime}\n"
        f"⭐ {rarity.title()}\n\n"
        f"💵 **Value:** {value} coins\n"
        f"💰 **Sell Price:** {sell_price} coins (50%)\n\n"
        f"⚠️ This cannot be undone!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^confirm_sell_(\d+)_(\d+)$"))
async def confirm_sell_callback(client: Client, callback: CallbackQuery):
    """Confirm waifu sale"""
    user_id = callback.from_user.id
    waifu_id = int(callback.matches[0].group(1))
    sell_price = int(callback.matches[0].group(2))

    # Get collection
    collection = await maybe_await(db.get_full_collection(user_id))
    
    if not collection:
        return await callback.answer("❌ Collection empty!", show_alert=True)

    # Find waifu
    waifu = None
    for w in collection:
        w_id = w.get("waifu_id") or w.get("id")
        try:
            if int(w_id) == waifu_id:
                waifu = w
                break
        except:
            continue

    if not waifu:
        return await callback.answer("❌ Waifu not found!", show_alert=True)

    name = waifu.get("waifu_name") or waifu.get("name", "Unknown")

    # Remove from collection and add coins
    await maybe_await(db.remove_from_collection(user_id, waifu_id))
    await maybe_await(db.add_coins(user_id, sell_price))

    try:
        await callback.message.edit_text(
            f"✅ **Waifu Sold!**\n\n"
            f"**Sold:** {name}\n"
            f"**Received:** {sell_price} coins\n\n"
            f"💰 Coins added to your balance!"
        )
    except Exception:
        try:
            await callback.message.reply_text(
                f"✅ **Waifu Sold!**\n\n"
                f"**Sold:** {name}\n"
                f"**Received:** {sell_price} coins"
            )
        except Exception:
            pass

    await callback.answer("✅ Sold!")


@Client.on_callback_query(filters.regex("^cancel_action$"))
async def cancel_action_callback(client: Client, callback: CallbackQuery):
    """Cancel any action"""
    try:
        await callback.message.edit_text("❌ Action cancelled.")
    except Exception:
        try:
            await callback.message.reply_text("❌ Action cancelled.")
        except Exception:
            pass
    await callback.answer()
