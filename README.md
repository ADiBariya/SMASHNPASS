# 🎴 SMASHNPASS — Waifu Smash & Pass Telegram Game Bot

> **⚠️ Age Restriction:** This bot contains suggestive, adult-oriented content.
> Only deploy and use where all players are **18 years of age or older.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-MTProto-informational?logo=telegram)](https://docs.pyrogram.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb)](https://www.mongodb.com/atlas)
[![GitHub issues](https://img.shields.io/github/issues/ADiBariya/SMASHNPASS)](https://github.com/ADiBariya/SMASHNPASS/issues)
[![GitHub stars](https://img.shields.io/github/stars/ADiBariya/SMASHNPASS?style=social)](https://github.com/ADiBariya/SMASHNPASS/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ADiBariya/SMASHNPASS?style=social)](https://github.com/ADiBariya/SMASHNPASS/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/ADiBariya/SMASHNPASS)](https://github.com/ADiBariya/SMASHNPASS/commits/main)
[![Code size](https://img.shields.io/github/languages/code-size/ADiBariya/SMASHNPASS)](https://github.com/ADiBariya/SMASHNPASS)
[![Top Language](https://img.shields.io/github/languages/top/ADiBariya/SMASHNPASS)](https://github.com/ADiBariya/SMASHNPASS)

A **Pyrogram-powered Telegram bot** that brings the classic *Smash or Pass* game to life with anime-style waifus.
Players collect characters, build their harem, earn coins, trade, marry, and compete on global leaderboards — all inside Telegram groups.

---

## 🔥 Key Features

| Feature | Description |
|---|---|
| 🎮 **Smash / Pass Game** | Vote on waifus; win them or lose the round |
| 🎲 **Auto Spawn** | Waifus automatically spawn in groups based on chat activity |
| 📦 **Collection System** | Paginated collection viewer; trade waifus with other users |
| 🏪 **Shop** | Spend coins on Common / Epic / Legendary / Rare / Premium boxes |
| 💰 **Daily Rewards** | Claim 100–500 coins per day with streak-multiplied bonuses |
| 💒 **Marriage System** | Propose to a waifu; acceptance chance varies by rarity |
| 🎁 **Gifting** | Gift a waifu or coins to any other player |
| 🏆 **Leaderboards** | Global rankings: top collectors, richest players, most wins |
| 👤 **Player Profiles** | Full stats, net worth, collection breakdown, global rank |
| 🖼️ **AI Scraper** | Owner tool to pull images from Aibooru into the waifu channel |
| 👑 **Admin Panel** | Broadcast, ban/unban, economy control, database maintenance |
| 📱 **Inline Mode** | Browse another player's collection via inline query |

---

## 🛠️ Tech Stack

- **Runtime:** Python 3.10+ with `asyncio`
- **Telegram Framework:** [Pyrogram](https://docs.pyrogram.org/) / [Pyrofork](https://github.com/KurimuzonAkuma/pyrogram)
- **Database:** MongoDB (sync via `pymongo`, async via `motor`)
- **Image Processing:** Pillow
- **Content Scraping:** `gallery-dl`, `aiohttp`
- **Deployment:** Heroku (`Procfile`) or any VPS

---

## ✅ Prerequisites

- Python **3.10 or higher**
- A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- A **Telegram API ID & API Hash** (from [my.telegram.org](https://my.telegram.org))
- A **MongoDB** database (local or [MongoDB Atlas](https://cloud.mongodb.com))
- A **Telegram user account** session string (userbot, for loading waifu images from a channel)
- A **Telegram channel** containing waifu images (caption format: `Name:`, `Anime:`, `Rarity:`)

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/ADiBariya/SMASHNPASS.git
cd SMASHNPASS
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Copy the example environment file and fill in your values:

```bash
cp .env .env.local   # edit .env.local — never commit real credentials
```

Then set the following variables (either in `.env` or as real environment variables):

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash from my.telegram.org |
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `MONGO_URI` | ✅ | MongoDB connection string (e.g. `mongodb+srv://...`) |
| `DB_NAME` | ✅ | MongoDB database name (default: `smashpassbot`) |
| `OWNER_ID` | ✅ | Your Telegram numeric user ID |
| `SUDO_USERS` | ⬜ | Space-separated list of trusted admin user IDs |
| `LOG_GROUP_ID` | ⬜ | Telegram group/channel ID for bot logs |
| `USER_SESSION` | ✅ | Pyrogram session string for the userbot account |
| `USERBOT_API_ID` | ✅ | API ID for the userbot account |
| `USERBOT_API_HASH` | ✅ | API Hash for the userbot account |
| `TG_WAIFU_CHANNEL` | ✅ | Numeric ID of the Telegram channel containing waifu images |
| `BOT_NAME` | ⬜ | Display name (default: `SmashWaifu`) |
| `SMASH_BASE_CHANCE` | ⬜ | Base win probability (default: `0.5`) |
| `COOLDOWN_SECONDS` | ⬜ | Smash cooldown in seconds (default: `10`) |

Additional game settings in [`config.py`](./config.py):

| Setting | Default | Description |
|---|---|---|
| `WIN_CHANCE` | `50` | % chance to win a waifu on Smash |
| `DAILY_COINS` | `100` | Base daily reward |
| `SMASH_COST` | `10` | Coin cost per Smash attempt |
| `COMMAND_PREFIX` | `["!", "/", "."]` | Accepted command prefixes |
| `RARITY_POINTS` | common=500, epic=1500, legendary=3000, rare=5000 | Sell value per rarity |

---

## 🚀 Running the Bot

```bash
python -B main.py
```

On startup the bot will:
1. Load all modules from `modules/`
2. Connect to MongoDB
3. Scan all Telegram groups and sync them to the database
4. Load waifu images from the configured Telegram channel via the userbot
5. Send a startup notification to the owner and (optionally) the log group

### Heroku Deployment

The repository includes a [`Procfile`](./Procfile) for Heroku worker dynos:

```
worker: python -B main.py
```

1. Create a Heroku app and set all environment variables as Config Vars.
2. Enable the **worker** dyno (not web).
3. Push the code and start the dyno.

---

## 🕹️ Commands Reference

### 👤 User Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and navigation menu |
| `/help` | Interactive help with per-module buttons |
| `/smash` `/waifu` `/sp` | Start a new Smash / Pass game round |
| `/cancel` | Cancel your active game |
| `/daily` `/claim` | Claim daily coin reward |
| `/streak` | Check your daily streak progress |
| `/bonus` | Claim 7-day streak bonus waifu |
| `/collection` `/col` | Browse your waifu collection |
| `/fav <id>` | Set a waifu as your favourite |
| `/waifuinfo <id>` | View detailed waifu info |
| `/trade @user` | Initiate a waifu trade |
| `/profile` `/p` | View your player profile |
| `/rename <name>` | Set your display name |
| `/marry` | Propose to a waifu from your collection |
| `/mywife` | See your currently married waifu |
| `/divorce` | Divorce your waifu |
| `/gift @user <id>` | Gift a waifu to another player |
| `/gift @user coins <n>` | Gift coins to another player |
| `/shop` | Browse the waifu shop |
| `/buy <item>` | Purchase a waifu box |
| `/sell <id>` | Sell a waifu for coins |
| `/balance` | Check your coin balance |
| `/leaderboard` `/lb` `/top` | Global leaderboards |
| `/stats` `/mystats` | Your personal statistics |
| `/ping` | Check bot latency and uptime |

### 👑 Admin / Owner Commands

| Command | Description |
|---|---|
| `/logs` | Retrieve bot log file (sudo only) |
| `/scangroups` `/syncgroups` | Re-scan and sync all groups to DB (sudo only) |
| `/restart` `/reboot` | Restart the bot (owner only) |
| `.addcoins @user <n>` | Add coins to a user |
| `.removecoins @user <n>` | Remove coins from a user |
| `.broadcast <msg>` | Broadcast message to all users |
| `.gcast <msg>` | Broadcast to all groups |
| `.bstats` | Full bot statistics |
| `.sudo add/remove/list` | Manage sudo users |
| `.ban` / `.unban @user` | Ban / unban users |
| `.addwaifu` | Add new waifu (reply to JSON) |
| `.delwaifu <id>` | Delete a waifu |
| `.syncwaifus` | Sync waifus from JSON to database |
| `/ai <tag>` | Search Aibooru for waifu images (owner/sudo) |
| `/setspawn` `/togglespawn` `/forcespawn` | Control group auto-spawn (admin) |
| `/autodel <seconds>` | Set auto-delete timer for games |

---

## 📁 Project Structure

```
SMASHNPASS/
├── main.py                  # Entry point — bot init, module loader, startup
├── config.py                # Configuration constants and env var loading
├── requirements.txt         # Python dependencies
├── Procfile                 # Heroku worker declaration
├── .env                     # Environment variable template (do NOT commit real values)
├── .gitignore
├── LICENSE                  # MIT License
│
├── core/
│   └── user_client.py       # Pyrogram userbot client (loads waifu images from channel)
│
├── database/
│   ├── __init__.py          # Exports `db` instance
│   └── mongo.py             # MongoDB Database class (users, groups, collections)
│
├── helpers/
│   ├── __init__.py
│   ├── utils.py             # WaifuManager, load_waifus, rarity helpers
│   ├── decorators.py        # Auth decorators (owner_only, sudo_only, etc.)
│   └── loader.py            # Module loading utilities
│
├── modules/                 # Dynamically loaded plugin modules
│   ├── smash.py             # 🎮 Core Smash/Pass game
│   ├── autospawn.py         # 🎲 Auto-spawn waifus in groups
│   ├── collection.py        # 📦 Collection viewer, trades, inline mode
│   ├── daily.py             # 📅 Daily rewards and streaks
│   ├── shop.py              # 🏪 Coin shop / waifu boxes
│   ├── leaderboard.py       # 🏆 Global leaderboards
│   ├── profile.py           # 👤 Player profiles
│   ├── marry.py             # 💒 Marriage system
│   ├── gift.py              # 🎁 Gifting system
│   ├── ai.py                # 🖼️ Aibooru scraper (owner tool)
│   ├── admin.py             # 👑 Admin commands
│   ├── start.py             # 🏠 /start, /stats
│   ├── alive.py             # ♻️ Alive / uptime check
│   ├── debug.py             # 🐛 Debug tools
│   ├── reload.py            # 🔄 Hot-reload modules
│   ├── scrapper.py          # 🌐 Content scraper utilities
│   ├── send.py              # 📤 Bulk send utilities
│   └── shau.py              # 🛡️ Extra owner utilities
│
├── data/
│   └── waifus.json          # Local waifu database (name, anime, rarity, image URL)
│
├── assets/
│   └── smash.jpg            # Game UI image asset
│
└── Cookies/                 # Session cookies for scrapers
```

---

## 🎴 Waifu Rarity System

| Rarity | Emoji | Sell Value | Shop Box Cost | Marriage Chance |
|---|---|---|---|---|
| Common | ⚪ | 500 | 500 coins | 80% |
| Epic | 🟣 | 1,500 | 1,500 coins | 40% |
| Legendary | 🟡 | 3,000 | 3,000 coins | 20% |
| **Rare** | 🔵 | **7,000** | **5,000 coins** | 60% |

> **Rare** is the highest tier in this game's rarity scale.

---

## 🗃️ Waifu Data Format

The bot loads waifus from two sources simultaneously:

**1. `data/waifus.json`** — local static list:
```json
{
  "waifus": [
    {
      "id": 1,
      "name": "Waifu Name",
      "anime": "Anime Series",
      "rarity": "legendary",
      "image": "https://example.com/image.jpg"
    }
  ]
}
```

**2. Telegram Channel** — loaded at startup via the userbot. Each post must be a photo with caption formatted as:
```
Name: <name>
Anime: <anime>
Rarity: <common|epic|legendary|rare>
```

---

## 🔒 Security Notes

- **Never commit your real `.env` values** to version control. The `.env` file in this repo contains placeholder values only; treat it as a template.
- `BOT_TOKEN`, `API_HASH`, `MONGO_URI`, and `USER_SESSION` are sensitive credentials — rotate them immediately if exposed.
- Admin commands (`/logs`, `.broadcast`, `.ban`, economy control) are gated behind `OWNER_ID` and `SUDO_USERS` checks defined in [`config.py`](./config.py) and [`main.py`](./main.py).
- The force-subscription check in `modules/smash.py` requires users to join the support group before playing.
- The AI scraper module is restricted to `OWNER_ID` and an explicit allowlist.
- Log files (`bot.log`) can only be retrieved by sudo users via `/logs`.

---

## 🧑‍💻 Development Workflow

1. Fork the repository and create a feature branch.
2. Install dependencies in a virtual environment (`pip install -r requirements.txt`).
3. Copy `.env` and fill in real credentials for local testing.
4. Run the bot locally: `python -B main.py`.
5. Modules are **hot-reloadable** via the `/reload` command (owner only).
6. Each module in `modules/` must expose `__MODULE__` (display name) and `__HELP__` (help text) at the top level — they are picked up automatically by the help system.

### Adding a New Module

Create `modules/myfeature.py`:
```python
from pyrogram import Client, filters
import config

__MODULE__ = "MyFeature"
__HELP__ = """
/mycommand - Does something cool
"""

@Client.on_message(filters.command("mycommand", config.COMMAND_PREFIX))
async def my_command(client, message):
    await message.reply_text("Hello!")
```

No further registration is required — `main.py` discovers and loads all `*.py` files in `modules/` automatically on startup.

---

## 🧪 Testing

There is currently no automated test suite in this repository.
Manual testing workflow:

1. Run the bot locally with a test bot token.
2. Add the bot to a test Telegram group.
3. Exercise commands via the Telegram client.

> 💡 **Suggested improvement:** Add a CI/CD workflow with `pytest` and mock Pyrogram clients to cover core game logic.

---

## 🗺️ Roadmap

- [ ] Add CI/CD pipeline (GitHub Actions) for linting and basic tests
- [ ] Persist auto-delete settings to MongoDB instead of a local JSON file
- [ ] Per-group NSFW toggle
- [ ] Voice line support via ElevenLabs
- [ ] Tournament / bracket mode
- [ ] Waifu upgrade / evolution system
- [ ] Web dashboard for bot statistics

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. **Fork** this repository.
2. **Create** a feature branch: `git checkout -b feature/awesome-feature`
3. **Commit** your changes: `git commit -m "feat: add awesome feature"`
4. **Push** to the branch: `git push origin feature/awesome-feature`
5. **Open** a Pull Request against `main`.

Please follow the existing code style and test your changes in a private Telegram environment before submitting.

---

## 👥 Contributors

<a href="https://github.com/ADiBariya/SMASHNPASS/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ADiBariya/SMASHNPASS" />
</a>

*Made with [contrib.rocks](https://contrib.rocks)*

---

## 📜 License

Copyright © 2026 **ADi** & **Shaurya**

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Pyrogram](https://docs.pyrogram.org/) / [Pyrofork](https://github.com/KurimuzonAkuma/pyrogram) — MTProto Telegram client
- [MongoDB](https://www.mongodb.com/) — Database backend
- [Aibooru](https://aibooru.online/) — AI-generated image source for admin scraper
- [catbox.moe](https://catbox.moe/) — Image hosting for bot assets
- [contrib.rocks](https://contrib.rocks/) — Contributors image generator

---

> **Play responsibly. All participants must be 18+.**

