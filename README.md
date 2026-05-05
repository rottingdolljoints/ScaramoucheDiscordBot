# Discord Tavern-Style LLM Chatbot

> **Archived project (2023).** This was one of my first big bot projects and is no longer maintained. It targets the LLM tooling landscape as it existed in mid-2023 — pinned dependency versions and the LangChain APIs used here have since moved on. Left up as a snapshot for reference and for anyone who wants to fork it.

A Discord bot that uses local LLMs and character cards (Pygmalion / TavernAI style) for casual roleplay chat. Supports both KoboldAI and Oobabooga's text-generation-webui as backends, and can auto-update the bot's avatar and display name to match the selected character.

![image](https://i.imgur.com/VPzquLom.png)

## Features

- **Character cards** — drop a Tavern-style PNG into `Cards/` or a JSON into `Characters/` and pick it at startup
- **Two LLM backends** — KoboldAI or Oobabooga (`text-generation-webui` with `--api`)
- **Per-channel memory** — sliding-window conversation history scoped to each channel
- **Image captions** — pasted images are run through BLIP and described back to the LLM
- **Stop sequences** — configurable per-bot stop tokens to cut off run-on generations
- **Listen-only mode** — bot reads but stays silent; toggle per channel via `/listen`
- **Ping mode** — when on, the bot replies to every message; when off, only when addressed (`/pingmode`)

## Setup

1. Clone this repo.
2. Copy `sample.env` to `.env` and fill in the values (see below).
3. Run `setup.bat` (Windows) or `setup.sh` (Linux/macOS) to create a virtualenv and install dependencies.
4. Run `run.bat` / `run.sh`.
5. Pick a character at the prompt.

> Discord only allows bots to be renamed twice per hour, so the auto-rename can fail silently on rapid restarts.

![Choose](https://i.imgur.com/qY6ZpB8.png)

### `.env` variables

| Variable | What it does |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Bot token from the [Discord Developer Portal](https://rentry.org/discordbotguide). |
| `ENDPOINT` | URL of your local LLM API. For Oobabooga running locally with `--api`, that's `http://127.0.0.1:5000/`. |
| `CHANNEL_ID` | Comma-separated list of channel IDs the bot is allowed to talk in. |
| `CHAT_HISTORY_LINE_LIMIT` | How many recent lines to keep in per-channel memory. |
| `STOP_SEQUENCES` | Comma-separated stop tokens. Use `\n\n` for blank-line stops. |
| `MAX_NEW_TOKENS` | Generation cap. KoboldAI maxes out at 512. |
| `ALWAYS_REPLY` | `T` = reply to every message; anything else = only when addressed. |

### Recommended LLM backend

Oobabooga's [text-generation-webui](https://github.com/oobabooga/text-generation-webui#one-click-installers) with `--api` enabled.

## Slash commands

If commands don't appear after startup, run `/sync` once to force a refresh.

| Command | What it does |
| --- | --- |
| `/sync` | Force-refresh the slash command tree. |
| `/reload <cog>` | Reload a single cog without restarting the bot. |
| `/test` | No-op sanity check. |
| `/listen` | Toggle listen-only mode for the current channel. |
| `/pingmode` | Toggle whether the bot replies to every message or only when addressed. |

## Tip: making the `.env` file on Windows

Enable file-name extensions so you can rename `sample.env.txt` → `.env`:

> Windows 11

![win11img](https://i.imgur.com/HayEcPol.png)

> Windows 10

![win10img](https://i.imgur.com/BsmMUjo.png)

![envgif](https://github.com/ausboss/PygDiscordBot/blob/main/how-to-env.gif)

## License

MIT — see [LICENSE](LICENSE).
