# Implementation Plan: Gmail Watcher (Bronze Tier)

**Plan:** 02_gmail_watcher.md
**Tier:** Bronze
**Status:** pending

---

## Goal

Add a Gmail watcher that polls the authenticated inbox for unread important emails
and writes `EMAIL_<message_id>.md` files into `Needs_Action/` — extending the same
`BaseWatcher` pattern used by the filesystem watcher.

---

## Prerequisites (one-time manual steps)

Before running any code the user must complete the Google Cloud setup:

- [X] Go to [Google Cloud Console](https://console.cloud.google.com/)
- [X] Create a new project (e.g. `ai-employee-vault`)
- [X] Enable the **Gmail API** for that project
- [X] Create **OAuth 2.0 credentials** → type: *Desktop app*
- [X] Download the credentials JSON file; rename it `credentials.json`
- [X] Place `credentials.json` in `Scripts/` (already gitignored via `.env` pattern — add explicit rule)
- [X] Run `Scripts/gmail_auth.py` once to complete the OAuth consent flow → produces `Scripts/token.json`

Both `credentials.json` and `token.json` must **never be committed** (add to `.gitignore`).

---

## Environment Variables (add to `.env`)

```
GMAIL_CREDENTIALS_PATH=Scripts/credentials.json
GMAIL_TOKEN_PATH=Scripts/token.json
GMAIL_QUERY=is:unread is:important
GMAIL_CHECK_INTERVAL=120
```

---

## New Dependencies

```
google-auth>=2.0
google-auth-oauthlib>=1.0
google-auth-httplib2>=0.2
google-api-python-client>=2.0
```

Add via: `uv add google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`

---

## Files to Create / Modify

| Action | File |
|--------|------|
| Create | `Scripts/gmail_auth.py` — standalone one-time OAuth flow script |
| Create | `Scripts/gmail_watcher.py` — `GmailWatcher(BaseWatcher)` implementation |
| Modify | `.gitignore` — add `Scripts/credentials.json`, `Scripts/token.json` |
| Modify | `Docs/02_Tier_Bronze.md` — update checklist to note Gmail watcher added |
| Modify | `Dashboard.md` — add Gmail watcher to system status |

---

## Implementation Steps

### Step 1 — Update `.gitignore`

Add to the secrets section:

```
Scripts/credentials.json
Scripts/token.json
```

### Step 2 — Create `Scripts/gmail_auth.py`

A standalone script the user runs **once** to complete the OAuth consent flow and
produce `token.json`. It is not part of the watcher loop.

Key behavior:
- Load `credentials.json` from env var `GMAIL_CREDENTIALS_PATH`
- Run `InstalledAppFlow` with scope `gmail.readonly`
- Save resulting token to `GMAIL_TOKEN_PATH`
- Print success message with token path

### Step 3 — Create `Scripts/gmail_watcher.py`

Extends `BaseWatcher`. Key design decisions:

**Authentication:**
- Load token from `GMAIL_TOKEN_PATH` (env var, default `Scripts/token.json`)
- Auto-refresh expired tokens; re-save refreshed token
- Raise `RuntimeError` with a clear message if token file is missing (direct user to run `gmail_auth.py`)

**State tracking:**
- Persist processed message IDs to `Scripts/.gmail_watcher_state.json` (gitignored)
- Load state on startup; save after each batch

**`check_for_updates()`:**
- Call `users().messages().list()` with the configured query
- Filter out already-processed IDs
- Return list of message dicts `{id, threadId}`

**`create_action_file(message)`:**
- Call `users().messages().get()` with `format=full` to get complete payload
- Extract headers: `From`, `To`, `Subject`, `Date`
- Decode body: prefer `text/plain` part; fall back to `snippet`
- Build frontmatter:
  ```yaml
  ---
  type: email
  status: pending
  priority: high
  created: <ISO 8601>
  source: gmail_watcher
  message_id: <gmail message id>
  thread_id: <thread id>
  from: <sender>
  to: <recipient>
  subject: <subject>
  date: <original send date>
  ---
  ```
- Write body section with full decoded text
- Write `## Suggested Actions` section with standard checkboxes
- Respect `DRY_RUN`: log intent but skip file write when `true`
- Append audit log entry to `Logs/YYYY-MM-DD.json`
- Mark message ID as processed in state file

**`run()` override:**
- Call `super().run()` — the base class loop handles scheduling and error recovery
- Log watcher startup with query and check interval

### Step 4 — Verify

- [X] `uv add google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dotenv`
- [X] In Google Cloud Console: create project → enable Gmail API → create OAuth Desktop credentials → download JSON
- [X] Rename downloaded file to `credentials.json` and place it at `Scripts/credentials.json`
- [X] `uv run python Scripts/gmail_auth.py` → browser opens → consent → `Scripts/token.json` created
- [X] In `.env` set `DRY_RUN=true`, then `uv run python Scripts/gmail_watcher.py` → logs emails found, no files written
- [X] In `.env` set `DRY_RUN=false`, then `uv run python Scripts/gmail_watcher.py` → `EMAIL_<id>.md` files appear in `Needs_Action/`

> **Windows note:** Do not use `VAR=value command` syntax (Unix only). Set variables in `.env`
> or use PowerShell inline: `$env:DRY_RUN="false"; uv run python Scripts/gmail_watcher.py`

---

## Issues & Resolutions

### Issue 1 — `DRY_RUN` not recognised on Windows
**Symptom:** Running `DRY_RUN=true uv run python Scripts/gmail_watcher.py` produced:
```
'DRY_RUN' is not recognized as an internal or external command
```
**Cause:** Inline `VAR=value command` is a Unix/bash-only syntax. Windows cmd and PowerShell do not support it.
**Fix:**
- Added `python-dotenv` (`uv add python-dotenv`) and called `load_dotenv()` at the top of `base_watcher.py` and `gmail_auth.py`.
- Users now control `DRY_RUN` and all other env vars via the `.env` file instead of the command line.
- Created `.env.example` as a committed template.
- PowerShell equivalent for one-off overrides: `$env:DRY_RUN="false"; uv run python Scripts/gmail_watcher.py`

### Issue 2 — Token file not found when run from `Scripts/` directory
**Symptom:** `RuntimeError: Token file not found: Scripts\token.json` when invoking the script from inside `Scripts/`.
**Cause:** `GMAIL_TOKEN_PATH=Scripts/token.json` in `.env` is a relative path. When the CWD is `Scripts/`, Python resolves it as `Scripts/Scripts/token.json` instead of `<vault_root>/Scripts/token.json`.
**Fix:** Added a `_resolve()` helper in both `gmail_watcher.py` (`__init__`) and `gmail_auth.py` (`main`) that anchors any relative path against the vault root (`self.vault_path`) or the script's own directory (`Path(__file__).parent`), respectively. Paths are now CWD-independent.
**Always run from vault root:**
```powershell
uv run python Scripts/gmail_watcher.py
```

---

## Out of Scope (this plan)

- Sending replies (requires `gmail.send` scope + HITL approval flow)
- Attachment handling
- Label management
- WhatsApp watcher (separate plan)
