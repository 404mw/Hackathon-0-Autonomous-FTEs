# Bronze Tier Implementation Plan — Phase 1: Folder Structure + Filesystem Watcher

## Context

We're on `tier/bronze` branch. Skills are done. Now we need the vault folder structure, foundational markdown files, and the filesystem watcher — the core Bronze deliverables.

## Step 1: Create Vault Folder Structure

Create all directories with `.gitkeep` files (so git tracks empty folders):

```
Inbox/
Needs_Action/
Plans/
In_Progress/
Pending_Approval/
Approved/
Rejected/
Done/
Accounting/
Briefings/
Logs/
Invoices/
Scripts/
```

## Step 2: Create Foundational Markdown Files

### `Company_Handbook.md`
- Communication style rules (email tone, response times)
- Approval thresholds (payments, emails, file ops, social media)
- Priority level definitions (urgent/high/normal/low)
- Quality standards
- Placeholder sections for client-specific rules

### `Business_Goals.md`
- Revenue targets (placeholder values)
- Key metrics table with alert thresholds
- Subscription audit rules
- Weekly audit checklist

### `Dashboard.md`
- System status section
- Pending messages table (empty initially)
- Recent activity log (empty initially)
- Critical alerts section
- YAML frontmatter with `last_updated` and `status`

## Step 3: Create `Scripts/base_watcher.py`

Abstract base class all watchers extend:
- `__init__(vault_path, check_interval)` — sets up paths + logger
- `check_for_updates()` — abstract, returns list of new items
- `create_action_file(item)` — abstract, creates `.md` in `Needs_Action/`
- `run()` — main loop with error handling + sleep
- DRY_RUN support via env var

## Step 4: Create `Scripts/filesystem_watcher.py`

Concrete watcher that monitors `Inbox/` for new files:
- Extends `BaseWatcher`
- Uses `watchdog` library for filesystem events (or polling fallback)
- On new file detected: creates `FILE_<name>.md` in `Needs_Action/` with YAML frontmatter
- Tracks processed files to avoid duplicates
- Respects DRY_RUN mode
- Logs actions via Python `logging` module

## Step 5: Add Dependencies

```
uv add watchdog ruff
```

## Step 6: Verification

- Drop a test file into `Inbox/`
- Run `uv run python Scripts/filesystem_watcher.py`
- Confirm `FILE_<name>.md` appears in `Needs_Action/` with correct frontmatter
- Confirm logging output works
- Confirm DRY_RUN mode prevents file creation when enabled

## Files to Create/Modify

| File | Action |
|------|--------|
| `Inbox/.gitkeep` | Create |
| `Needs_Action/.gitkeep` | Create |
| `Plans/.gitkeep` | Create |
| `In_Progress/.gitkeep` | Create |
| `Pending_Approval/.gitkeep` | Create |
| `Approved/.gitkeep` | Create |
| `Rejected/.gitkeep` | Create |
| `Done/.gitkeep` | Create |
| `Accounting/.gitkeep` | Create |
| `Briefings/.gitkeep` | Create |
| `Logs/.gitkeep` | Create |
| `Invoices/.gitkeep` | Create |
| `Scripts/.gitkeep` | Create |
| `Company_Handbook.md` | Create |
| `Business_Goals.md` | Create |
| `Dashboard.md` | Create |
| `Scripts/base_watcher.py` | Create |
| `Scripts/filesystem_watcher.py` | Create |
| `pyproject.toml` | Modify (add watchdog dep) |
