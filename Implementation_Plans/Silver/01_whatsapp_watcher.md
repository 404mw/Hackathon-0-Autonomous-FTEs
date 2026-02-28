# Silver Plan 01 — WhatsApp Watcher

## Overview

Playwright-based watcher that monitors WhatsApp Web for unread messages,
filters by business-relevant keywords, and creates `WHATSAPP_*.md` files
in `Needs_Action/` for the AI Employee to triage.

## Approach

WhatsApp has no public API. We use **Playwright** with a **persistent browser
context** (saves the WhatsApp Web session/QR scan across restarts).

**Check interval:** 30 seconds
**Session storage:** `Scripts/.whatsapp_session/` (excluded from git)
**Keyword filter:** configurable via `WHATSAPP_KEYWORDS` env var
**Default keywords:** `urgent, asap, invoice, payment, help, question, project`

## File Naming

```
WHATSAPP_<sanitised_contact>_<YYYY-MM-DD_HHMM>.md
```

## Frontmatter

```yaml
---
type: whatsapp
status: pending
priority: high | normal
created: <ISO 8601>
source: whatsapp_watcher
contact: "<display name>"
message_preview: "<first 200 chars>"
---
```

## Steps

- [x] 1. Add `playwright` to `pyproject.toml` — installed playwright==1.58.0
- [x] 2. Add `playwright install chromium` setup note (see below)
- [x] 3. Create `Scripts/whatsapp_watcher.py` extending `BaseWatcher`
- [x] 4. Implement `check_for_updates()` — Playwright persistent context,
       JS evaluate for unread badge scrape, multi-selector fallbacks
- [x] 5. Implement `create_action_file()` — `WHATSAPP_*.md` with frontmatter,
       priority escalation for urgent keywords
- [x] 6. Implement `_load_state()` / `_save_state()` — contact→preview_hash
       dedup (same JSON pattern as GmailWatcher)
- [x] 7. First-run: headful launch + `input()` wait; headless on subsequent
       runs; session-expired detection with clear re-auth message
- [x] 8. `_write_audit_log()` — same schema as GmailWatcher
- [x] 9. `.env.example` and `.gitignore` updated with WhatsApp vars +
       session/state paths gitignored
- [ ] 10. Manual smoke-test: scan QR, send test message, confirm `.md` created

## One-time Chromium Setup

Before first run, install the Chromium browser binary:
```bash
uv run playwright install chromium
```

## Dependencies

```
playwright>=1.44
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_SESSION_PATH` | `Scripts/.whatsapp_session` | Playwright persistent context dir |
| `WHATSAPP_KEYWORDS` | `urgent,asap,invoice,payment,help` | CSV of trigger keywords |
| `WHATSAPP_CHECK_INTERVAL` | `30` | Seconds between polls |
| `DRY_RUN` | `true` | Inherited from BaseWatcher |

## Files Created

- `Scripts/whatsapp_watcher.py`
- `Scripts/.whatsapp_session/` (runtime, gitignored)
- `Scripts/.whatsapp_watcher_state.json` (runtime, gitignored)

## Issues & Resolutions

### Issue 1 — State saved unconditionally before DRY_RUN guard

**Symptom:** In the initial implementation of `create_action_file()`, the state
update (`self._processed[contact] = preview_hash` + `self._save_state()`) was
called unconditionally before the `if self.dry_run` check. In dry_run mode this
meant state was persisted but no audit log was written — inconsistent with
`GmailWatcher` and misleading (state implies something was actioned).

**Root cause:** State save was placed before the dry_run guard to "prevent
duplicates even if the write fails", but this diverged from the Bronze
watcher pattern where state is saved *inside* each branch.

**Fix:** Moved state save into both branches, mirroring `GmailWatcher` exactly:
- `dry_run` path: log + save state + return None (no audit log)
- real path: write file + save state + write audit log + return path
