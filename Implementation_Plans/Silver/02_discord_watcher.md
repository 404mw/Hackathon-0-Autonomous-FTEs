# Silver Plan 02 — Discord Watcher

## Overview

A `discord.py` bot that connects to a Discord server, monitors configured
channels and DMs for new messages, and creates `DISCORD_*.md` files in
`Needs_Action/` for the AI Employee to triage.

## Library Choice: discord.py 2.x (not nextcord)

`nextcord` was a fork created in 2021 when discord.py was abandoned. Discord.py
was **revived in 2022** by its original author (Rapptz) and is now fully
maintained at 2.x. We use discord.py because it has the larger community,
better docs, and no feature gaps for our use case.

## Approach

Unlike Playwright-based scrapers, Discord has a well-supported **bot API**
via `discord.py`. The bot connects via websocket (event-driven — no polling
needed), so latency is near-instant.

**Trigger:** `@mention` in server channels; all messages in DMs
**Filter:** configurable channel IDs (empty = all channels); no keyword filter
**Session:** bot token (stored in `.env`)

## File Naming

```
DISCORD_<sanitised_channel>_<message_id>.md
```

## Frontmatter

```yaml
---
type: discord
status: pending
priority: high | normal
created: <ISO 8601>
source: discord_watcher
trigger: mention | dm
guild: "<server name>"
channel: "<channel name>"
author: "<username>"
message_id: "<snowflake>"
message_preview: "<first 200 chars>"
---
```

## Architecture Note

`discord.py` is event-driven (asyncio), which is different from the
polling-based `BaseWatcher`. We will:

1. Keep the `DiscordWatcher` as a **thin adapter** — it uses discord.py's
   event loop internally but still extends `BaseWatcher`.
2. Override `run()` to start the discord.py bot instead of the default
   polling loop.
3. `check_for_updates()` returns `[]` (no-op — events arrive via callbacks).
4. `create_action_file()` is called directly from `on_message` callback.

## Steps

- [x] 1. `uv add discord.py` — installed discord-py==2.6.4
- [x] 2. Bot setup instructions documented in script docstring (Developer Portal,
       Message Content Intent, bot scope + Read Messages perm)
- [x] 3. Created `Scripts/discord_watcher.py`:
       - `DiscordWatcher(BaseWatcher)` — overrides `run()` with `bot.run(token)`
       - `_build_bot()` registers `on_ready` + `on_message` closures
       - `_handle_message()` — trigger: `@mention` in channels, all DMs;
         no keyword filter; dedup by message snowflake ID
       - `create_action_file()` writes `DISCORD_*.md` with `trigger` field —
         DRY_RUN pattern matches GmailWatcher (state saved inside each branch)
- [x] 4. `_write_audit_log()` implemented (same schema as other watchers)
- [x] 5. `.env.example` updated — `DISCORD_KEYWORDS` removed, channel/DM vars kept
- [ ] 6. Smoke test: post a message in the configured channel, confirm `.md`

## Dependencies

```
discord.py>=2.3
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | _(required)_ | Bot token from Discord Developer Portal |
| `DISCORD_CHANNEL_IDS` | _(empty = all)_ | CSV of channel IDs where @mentions are watched |
| `DISCORD_MONITOR_DMS` | `true` | Whether to process DMs to the bot |
| `DRY_RUN` | `true` | Inherited from BaseWatcher |

## Files Created

- `Scripts/discord_watcher.py`
- `Scripts/.discord_watcher_state.json` (runtime, gitignored)

## Issues & Resolutions

### Issue 2 — Design change: keywords → @mention trigger

**Symptom:** Initial design used a keyword filter (`DISCORD_KEYWORDS`) to
decide which server messages to act on, matching WhatsApp's approach.

**Root cause:** Keyword filtering is a poor fit for Discord — a bot that
silently reads all messages looking for keywords is unexpected behaviour.
The natural Discord pattern is to @mention the bot when you need it.

**Fix:** Removed `keywords` parameter and `self.keywords` attribute entirely.
Replaced keyword check in `_handle_message()` with:
- Server channels: `self._bot.user in message.mentions` — only fires on @mention
- DMs: always fires (user is already addressing the bot directly)

Added `trigger: mention | dm` field to item dict and YAML frontmatter.
Removed `DISCORD_KEYWORDS` from `.env.example`.

---

### Issue 1 — Unused `safe_content` variable (ruff F841)

**Symptom:** `safe_content = content[:200].replace('"', "'")` was computed
in `create_action_file()` but the f-string used the raw `content` variable
instead, leaving `safe_content` unused. Ruff flagged F841.

**Root cause:** Variable was prepared for YAML safety but not wired into
the frontmatter field.

**Fix:** Added `message_preview: "{safe_content}"` to the YAML frontmatter,
consuming the variable and making the preview YAML-safe.
