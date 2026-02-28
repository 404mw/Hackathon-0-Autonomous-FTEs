# Scripts — AI Employee Vault

All watcher scripts, the orchestrator, and the MCP server live here.

---

## Quick Start

### 1 — Copy and fill in secrets

```powershell
copy .env.example .env
# Edit .env with your API keys and tokens
```

### 2 — Authenticate services (run once each)

```powershell
# Gmail (required for email watcher + email send MCP)
uv run python Scripts\gmail_auth.py

# LinkedIn poster (required for linkedin-posting skill)
uv run python Scripts\linkedin_auth.py

# WhatsApp — run the watcher once; it opens a browser for QR scan
uv run python Scripts\whatsapp_watcher.py

# LinkedIn watcher — run once; it opens a browser for login
uv run python Scripts\linkedin_watcher.py

# Discord — no interactive auth needed; set DISCORD_BOT_TOKEN in .env
```

### 3 — Smoke test (DRY_RUN=true, no external calls)

```powershell
# Each watcher runs for a few seconds then Ctrl+C to stop
uv run python Scripts\gmail_watcher.py
uv run python Scripts\discord_watcher.py
uv run python Scripts\orchestrator.py
```

### 4 — Go live (flip DRY_RUN=false in .env, then start everything)

See **PM2** or **Task Scheduler** sections below.

---

## Watcher Scripts

| Script | Purpose | Check interval |
|--------|---------|---------------|
| `filesystem_watcher.py` | Monitors `Inbox/` for dropped files | 5 s (watchdog) |
| `gmail_watcher.py` | Polls Gmail for unread important emails | 120 s |
| `whatsapp_watcher.py` | Scrapes WhatsApp Web via Playwright | 60 s |
| `discord_watcher.py` | discord.py bot, event-driven | instant |
| `linkedin_watcher.py` | Scrapes LinkedIn messages via Playwright | 120 s |

All watchers write action files to `Needs_Action/` and audit logs to `Logs/`.

---

## Orchestrator

`orchestrator.py` polls `Approved/` every 10 seconds and dispatches approved
actions without requiring Claude Code to be open.

```powershell
uv run python Scripts\orchestrator.py
```

**Supported actions:**

| `action` field | Handler |
|---------------|---------|
| `send_email` | Gmail API (sends via OAuth token) |
| `post_linkedin` | `linkedin_poster.py` → LinkedIn UGC Posts API |
| `discord_reply` | Logs manual instructions to console |
| `whatsapp_reply` | Logs manual instructions to console |

---

## PM2 — Recommended Process Manager

PM2 keeps all processes alive, auto-restarts on crash, and persists across reboots.

### Install

```powershell
npm install -g pm2
```

### Start all (DRY_RUN=true, safe default)

```powershell
cd G:\Hackathons\GIAIC_Hackathons\AI_Employee_Vault
pm2 start Scripts\pm2.config.js
```

### Start all in production (DRY_RUN=false)

```powershell
pm2 start Scripts\pm2.config.js --env prod
```

### Persist across reboots

```powershell
pm2 save
pm2 startup   # follow the printed instructions to register the startup command
```

### Common commands

```powershell
pm2 status          # show all process states
pm2 logs            # tail all logs (Ctrl+C to exit)
pm2 logs gmail-watcher   # tail a single process
pm2 restart all     # restart all processes
pm2 stop all        # stop all processes
pm2 delete all      # remove all from PM2 registry
```

Log files are written to `Logs/pm2-<name>-out.log` and `Logs/pm2-<name>-error.log`.

---

## Windows Task Scheduler — Alternative

Use this if you prefer not to install PM2. XML templates are in `Scripts\task-scheduler\`.

### Import all tasks (run as Administrator)

```powershell
$vault = "G:\Hackathons\GIAIC_Hackathons\AI_Employee_Vault"
$xmlDir = "$vault\Scripts\task-scheduler"

schtasks /Create /XML "$xmlDir\gmail_watcher.xml"        /TN "AI-Employee\gmail-watcher"        /F
schtasks /Create /XML "$xmlDir\whatsapp_watcher.xml"     /TN "AI-Employee\whatsapp-watcher"     /F
schtasks /Create /XML "$xmlDir\discord_watcher.xml"      /TN "AI-Employee\discord-watcher"      /F
schtasks /Create /XML "$xmlDir\linkedin_watcher.xml"     /TN "AI-Employee\linkedin-watcher"     /F
schtasks /Create /XML "$xmlDir\linkedin_post_schedule.xml" /TN "AI-Employee\linkedin-post-schedule" /F
```

**Before importing:** open each XML and replace `YOUR-PC\your-username` with your
actual Windows username (e.g. `DESKTOP-ABC\404mw`).

### Manage tasks

```powershell
schtasks /Run /TN "AI-Employee\gmail-watcher"    # start immediately
schtasks /End /TN "AI-Employee\gmail-watcher"    # stop
schtasks /Delete /TN "AI-Employee\gmail-watcher" /F  # remove
schtasks /Query /TN "AI-Employee" /FO LIST       # show all AI-Employee tasks
```

---

## Email Send MCP Server

Registered with Claude Code so the `send_email`, `draft_email`, and `list_drafts`
tools are available inside Claude Code sessions.

### Register (run once)

```powershell
claude mcp add email-send -s project -- uv --directory "G:/Hackathons/GIAIC_Hackathons/AI_Employee_Vault" run python Scripts/mcp_servers/email_send/server.py
```

Configuration is saved to `.mcp.json` in the vault root.

---

## LinkedIn Post Trigger

Creates a post trigger file on demand (normally run by the Task Scheduler):

```powershell
uv run python Scripts\linkedin_post_trigger.py
```

This writes `Needs_Action\LINKEDIN_POST_TRIGGER_<YYYY-MM-DD>.md`, which
signals Claude Code to invoke the `/linkedin-posting` skill.

---

## Environment Variables

Key variables (see `.env.example` for the full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `DRY_RUN` | `true` | Set `false` to enable live external actions |
| `VAULT_PATH` | parent of `Scripts/` | Override vault root path |
| `GMAIL_CHECK_INTERVAL` | `120` | Gmail poll interval (seconds) |
| `ORCHESTRATOR_INTERVAL` | `10` | Approved/ scan interval (seconds) |
| `DISCORD_BOT_TOKEN` | — | Discord bot token (required) |
| `LINKEDIN_ACCESS_TOKEN` | — | LinkedIn OAuth token |
| `LINKEDIN_PERSON_URN` | — | `urn:li:person:<id>` from `linkedin_auth.py` |
