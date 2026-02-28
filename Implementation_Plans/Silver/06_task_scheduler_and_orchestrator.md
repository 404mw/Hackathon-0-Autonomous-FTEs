# Silver Plan 06 — Task Scheduler & Orchestrator

## Overview

Two components:

1. **Windows Task Scheduler** — auto-start all watchers on login/boot, with
   crash recovery via PM2 or the scheduler's built-in retry.
2. **Orchestrator script** — a lightweight Python script that watches the
   `Approved/` folder and dispatches approval actions (bridges HITL files to
   actual execution without needing Claude to be open).

## Part A — Process Management

### PM2 (recommended over raw Task Scheduler)

PM2 is a Node.js process manager that runs Python scripts too. It handles:
- Auto-restart on crash
- Log rotation
- Startup on Windows boot (via `pm2 startup`)

```bash
# Install PM2 globally
npm install -g pm2

# Start watchers
pm2 start Scripts/gmail_watcher.py   --name gmail-watcher    --interpreter python
pm2 start Scripts/whatsapp_watcher.py --name whatsapp-watcher --interpreter python
pm2 start Scripts/discord_watcher.py  --name discord-watcher  --interpreter python
pm2 start Scripts/linkedin_watcher.py --name linkedin-watcher --interpreter python

# Save list & enable startup
pm2 save
pm2 startup
```

Config file: `Scripts/pm2.config.js`

### Fallback: Windows Task Scheduler XML

For each watcher, a Task Scheduler XML that:
- Triggers on user login
- Runs `uv run python Scripts/<watcher>.py` in vault directory
- Restarts on failure (up to 3 times, 1-minute intervals)

Files in `Scripts/task-scheduler/`:
- `gmail_watcher.xml`
- `whatsapp_watcher.xml`
- `discord_watcher.xml`
- `linkedin_watcher.xml`

## Part B — Approval Orchestrator

A lightweight watcher that monitors `Approved/` and dispatches actions —
so approvals can be executed without opening Claude Code.

```
Scripts/orchestrator.py
```

### Behavior

```
Loop every 10s:
  scan Approved/ for *.md files
  for each file:
    read action type from frontmatter
    dispatch to appropriate handler:
      send_email  → gmail_send.py helper (or MCP via subprocess)
      linkedin_post → linkedin_poster.py
      whatsapp_reply → log as manual (no auto-send)
      discord_reply  → discord_reply.py helper (future)
    move file to Done/
    write audit log
```

### Note on DRY_RUN

The orchestrator respects `DRY_RUN=true`. When dry run, it logs what it
*would* do but does not call any external service.

## Part C — LinkedIn Posting Schedule

A separate scheduled task that runs the `linkedin-posting` skill on schedule:

```
Task: linkedin-post-trigger
Schedule: Mon, Wed, Fri at 09:00
Action: Run linkedin_post_trigger.py which writes a trigger file to Inbox/
```

The trigger file causes vault-triaging → linkedin-posting → HITL flow.

## Steps

- [x] 1. Create `Scripts/pm2.config.js` with all watcher definitions
- [x] 2. Create `Scripts/task-scheduler/` with XML files for each watcher
       (backup for users who prefer not to use PM2)
- [x] 3. Create `Scripts/orchestrator.py` — approval dispatcher loop
- [x] 4. Create `Scripts/linkedin_post_trigger.py` — writes a trigger file
- [x] 5. Create Task Scheduler XML for linkedin post schedule
- [x] 6. Add README to `Scripts/` documenting how to start everything
- [x] 7. ~~Add pm2 install + startup instructions to `Docs/01_Prerequisites_Setup.md`~~
       **REVERTED** — `Docs/` is read-only reference material; see `Scripts/README.md` instead
- [x] 8. Smoke test: approve a test file, confirm orchestrator dispatches it

## Files Created

- `Scripts/pm2.config.js`
- `Scripts/orchestrator.py`
- `Scripts/linkedin_post_trigger.py`
- `Scripts/start-hidden.vbs`
- `Scripts/task-scheduler/gmail_watcher.xml`
- `Scripts/task-scheduler/whatsapp_watcher.xml`
- `Scripts/task-scheduler/discord_watcher.xml`
- `Scripts/task-scheduler/linkedin_watcher.xml`
- `Scripts/task-scheduler/linkedin_post_schedule.xml`
- `Scripts/task-scheduler/pm2_startup.xml`

## Issues & Resolutions

### Issue 1 — UnicodeEncodeError on Windows cp1252 console

**Symptom:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2014'`
on the StreamHandler when the orchestrator logged messages containing em dashes (—)
or box-drawing characters (─).

**Root cause:** Windows console defaults to code page 1252 (cp1252), which does
not map all Unicode characters. Python's logging `StreamHandler` inherits the
console's codec and fails on characters outside cp1252.

**Fix:** Replaced all non-ASCII characters in `logger.*` call strings with ASCII
equivalents: em dash `—` → `--`, box-drawing `─` → `-`, arrow `→` → `->`.
Docstring text is unaffected (never written to the console at runtime).

### Issue 2 — PM2 PowerShell wrapper broke log capture and caused crash-loop

**Symptom:** All 5 PM2 processes showed `waiting...` status with 34+ restarts and
zero log output. Restarting didn't help.

**Root cause:** To suppress CMD windows, the `cmd()` helper was changed to wrap
every process in `powershell -NonInteractive -WindowStyle Hidden -Command "uv ..."`.
PM2 then monitored `powershell.exe` (not `uv`/Python). PowerShell silently failed
on the args quoting, exited instantly, and PM2 saw a crash → restart loop. PM2
cannot pipe stdout/stderr from a grandchild process so logs were empty.

**Fix:** Reverted `cmd()` to run `uv` directly with `interpreter: "none"` and added
`windowsHide: true` to the app config, which passes `CREATE_NO_WINDOW` via Node.js
`child_process.spawn()`. This resolved the crash loop and restored log capture.

### Issue 3 — `pm2 startup` not supported on Windows

**Symptom:** `pm2 startup` threw `Error: Init system not found`.

**Root cause:** PM2's `startup` command only supports Linux (systemd) and macOS
(launchd). Windows is not supported.

**Fix:** Created `Scripts/start-hidden.vbs` (VBScript launcher) and
`Scripts/task-scheduler/pm2_startup.xml` (Task Scheduler XML) as the Windows
auto-start solution. Import the XML with `schtasks /Create /XML`.

### Issue 4 — PM2 processes still showed 5 CMD windows despite `windowsHide: true`

**Symptom:** After fixing the crash loop, 5 visible CMD windows appeared — one
per watcher. Closing them caused PM2 to restart the process (correct PM2 behaviour,
wrong UX).

**Root cause:** When the PM2 daemon (which has no console of its own) spawns a
child process, Windows allocates a new console for any console-subsystem application
unless `CREATE_NO_WINDOW` is explicitly set. PM2's `windowsHide: true` config option
is supposed to set this flag via `child_process.spawn()`, but the flag did not
propagate to PM2's spawned children in practice (likely a PM2 version or platform
bug).

**Fix:** Switched from `python` to `pythonw.exe` (the Windows windowless Python
executable found at `.venv/Scripts/pythonw.exe`). `pythonw.exe` is compiled as a
Windows GUI-subsystem application, so Windows never allocates a console for it
regardless of how it is spawned. PM2 config updated:

```javascript
const PYTHONW = `${VAULT}/.venv/Scripts/pythonw.exe`;
function cmd(script) {
  return { script: PYTHONW, args: `Scripts/${script}`, interpreter: "none" };
}
```

Python automatically adds the script's own directory (`Scripts/`) to `sys.path[0]`,
so `from base_watcher import BaseWatcher` continues to work. PM2 still captures
stdout/stderr to the configured log files via pipes.
