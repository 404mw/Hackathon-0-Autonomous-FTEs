# Silver Plan 04 — Email Send MCP Server (Python)

## Library Choice: Python MCP (not TypeScript)

Anthropic ships an official Python MCP SDK (`mcp`, installable via `uv add mcp`).
We use Python because:
- Same runtime as every other script — `uv` already manages it, no Node.js needed
- Can directly import existing `google-api-python-client` auth code; no bridge
- No `tsconfig.json`, no build step, no `dist/` folder to maintain
- One fewer runtime to debug in production

## Overview

A **Python MCP server** that exposes `send_email` and `draft_email` tools to
Claude Code. This is the "hands" that allow the AI Employee to send emails —
but only after HITL approval has been granted.

## Architecture

```
approval-executing skill
  → reads Approved/EMAIL_SEND_*.md
  → calls MCP tool: send_email(to, subject, body, thread_id?)
  → MCP server reuses token.json → Gmail API send
  → result logged to Logs/
  → file moved to Done/
```

## MCP Server Structure

```
Scripts/mcp_servers/
└── email_send/
    ├── __init__.py
    └── server.py        # MCP server entry point
```

(Python convention: `snake_case` directories, no build step)

## Tools Exposed

### `send_email`
Send an email via Gmail API.

```python
# Input schema
{
    "to": str,                   # recipient address
    "subject": str,
    "body": str,                 # plain text
    "cc": str | None,
    "reply_to_thread_id": str | None,   # for Gmail threading
}
# Returns
{
    "message_id": str,
    "thread_id": str,
    "timestamp": str,            # ISO 8601
}
```

### `draft_email`
Save a Gmail draft (no send). Used by `email-drafting` skill for review.

```python
# Input schema
{
    "to": str,
    "subject": str,
    "body": str,
    "cc": str | None,
}
# Returns
{
    "draft_id": str,
    "timestamp": str,
}
```

### `list_drafts`
Return recent draft subjects for review — no extra params needed.

## Gmail API Scopes

Current `token.json` has: `gmail.readonly`
Add for MCP server: `gmail.send`

**Action required:** Update `gmail_auth.py` SCOPES to include
`https://www.googleapis.com/auth/gmail.send`, delete `Scripts/token.json`,
re-run `uv run python Scripts/gmail_auth.py`.

## Implementation Pattern

```python
# Scripts/mcp_servers/email_send/server.py
from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64, os
from email.mime.text import MIMEText

mcp = FastMCP("email-send")

@mcp.tool()
def send_email(to: str, subject: str, body: str, ...) -> dict:
    """Send an email via Gmail API."""
    if os.environ.get("DRY_RUN", "true").lower() == "true":
        return {"dry_run": True, "would_send_to": to}
    ...

if __name__ == "__main__":
    mcp.run()
```

Uses `FastMCP` (the high-level API from the `mcp` package) — minimal boilerplate.

## Steps

- [x] 1. `uv add mcp` — installed mcp==1.26.0
- [x] 2. Created `Scripts/mcp_servers/__init__.py` (empty)
- [x] 3. Created `Scripts/mcp_servers/email_send/__init__.py` (empty)
- [x] 4. Created `Scripts/mcp_servers/email_send/server.py`:
       - `FastMCP("email-send")` instance
       - `send_email` tool: `MIMEText` → base64url → `gmail.users.messages.send`;
         `threadId` support for replies; DRY_RUN guard
       - `draft_email` tool: `gmail.users.drafts.create`; DRY_RUN guard
       - `list_drafts` tool: returns last 10 drafts (empty list in DRY_RUN)
       - `_get_gmail_service()` helper: loads token.json, auto-refreshes,
         uses both `gmail.readonly` + `gmail.send` scopes
- [x] 5. Updated `Scripts/gmail_auth.py` SCOPES → added `gmail.send`;
       docstring updated with note to delete token.json before re-running
- [x] 6. Registered MCP server in Claude Code (project scope via `.mcp.json`):
       ```bash
       claude mcp add email-send -s project -- \
         uv --directory "G:/Hackathons/GIAIC_Hackathons/AI_Employee_Vault" \
         run python Scripts/mcp_servers/email_send/server.py
       ```
- [ ] 7. Smoke test with `DRY_RUN=true`: call `send_email`, verify log output
- [ ] 8. Integration test: approve a test email, confirm full HITL→send flow

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GMAIL_TOKEN_PATH` | Path to token.json (must include `gmail.send` scope) |
| `GMAIL_CREDENTIALS_PATH` | Path to credentials.json |
| `DRY_RUN` | `"true"` → log only, do not send |

## Files Created

- `Scripts/mcp_servers/__init__.py`
- `Scripts/mcp_servers/email_send/__init__.py`
- `Scripts/mcp_servers/email_send/server.py`

## Issues & Resolutions

_(Document bugs here as encountered.)_
