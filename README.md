18+
# 💋 Waifu TG — Smash & Pass Game Bot

> A cheeky, flirt-friendly Telegram game bot that plays the classic *Smash / Pass* with anime-style waifus. Designed to be playful, interactive, and (optionally) a little sultry — without crossing into explicit content.

**⚠️ Age restriction:** This bot contains suggestive, adult-oriented roleplay. Only deploy and use if all players are **18+**.

---

## 🔥 What this repo contains

* A Telegram bot that runs a waifu-themed Smash/Pass mini-game with chatbot features.

---

## 🎯 Features (Playful / Non-explicit)

* `smash` / `pass` voting flows with animated embeds

---


<details>
<summary>2) Configure & run</summary>

```bash
# copy example env and edit
cp .env.example .env
# set TG_TOKEN, DB_URL (optional), NSFW_MODE=true/false
npm install
npm start
```

</details>

<details>
<summary>3) Invite & test</summary>

* Add the bot to a group or open a private chat.
* Try `/help` to see commands.

</details>

---

## 🕹 Commands (examples)

| Command               |                               What it does | Notes                              |                               |
| --------------------- | -----------------------------------------: | ---------------------------------- | ----------------------------- |
| `/smashpass`          | Start a new round (creates a poll-like UI) | Group-only by default              |                               |
| `/vote <id> smash     |                                      pass` | Cast your vote                     | Quick inline buttons included |
| `/profile`            |            View your waifu cards & rewards | Private chat                       |                               |
| `/persona set <name>` |                     Switch bot personality | e.g. `tsundere`                    |                               |
| `/mature on           |                                       off` | Toggle suggestive lines (18+ only) | Admin-only                    |

---

## ✨ Interactive README extras

* Collapsible persona examples (below) show sample lines for each personality.

<details>
<summary>Persona: Tsundere</summary>

> "W-what are you staring at? It's not like I enjoy your votes or anything... baka."

</details>

<details>
<summary>Persona: Shy</summary>

> "Oh— um, you picked me? That's… nice. Thank you."

</details>

---

## 🔧 Configuration

Place the following in `.env`:

```
TG_TOKEN=123456:ABC-DEF...   # your bot token
DB_URL=mongodb://...         # optional, for profiles & rewards
NSFW_MODE=false              # false = PG-13 flirty; true = suggestive, non-explicit
VOICE_PROVIDER=elevenlabs    # optional voice lines
```

---

## 🛡 Safety & Moderation

* Always enable the age-gate. Display an 18+ confirmation before mature content.
* The repo intentionally avoids explicit sexual descriptions — keep it suggestive and playful.


---

## ❤️ License & Credits

Built with love. Use responsibly.

---

