---
name: approval-executing
description: Executes approved actions from Approved/. Routes by action field to send_email MCP tool, linkedin_poster.py, or manual reply instructions, then moves the file to Done/ and logs the result. Use when files appear in Approved/ or when the user confirms an approval.
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Approval Executing

Executes actions from files in `Approved/` and closes the HITL loop by moving
them to `Done/` and writing the audit log.

## When to Invoke

- When a file appears in `Approved/` (moved there by the user)
- When the user says "execute approved actions", "run approved", or similar
- After the user confirms they have moved an approval file to `Approved/`

## Execution Flow

1. **Glob** for all `.md` files in `Approved/`
2. For each file:
   a. **Read** the file and extract frontmatter fields: `action`, `status`, `expires`
   b. **Check expiry** — if `expires` is set and has passed, skip execution,
      log an error, and notify the user to re-create the approval
   c. **Route** by `action` field (see table below)
   d. **Mark** the file's `status` as `done` in its frontmatter
   e. **Move** the file from `Approved/` to `Done/` (Write new + note original removed)
   f. **Log** result via `audit-logging`
3. **Update** `dashboard-updating` when all files are processed

## Action Routing Table

| `action` value | Executor | Notes |
|----------------|----------|-------|
| `send_email` | MCP `send_email` tool | Pass `to`, `subject`, `thread_id` from frontmatter; body from draft section |
| `draft_email` | MCP `draft_email` tool | Creates Gmail draft; does not send |
| `post_linkedin` | `Bash: uv run python Scripts/linkedin_poster.py` | Pass post text from draft section |
| `discord_reply` | Manual instructions | Log the reply text; instruct user to post manually in Discord |
| `whatsapp_reply` | Manual instructions | Log the reply text; instruct user to send manually in WhatsApp |

## send_email Execution Detail

Read these fields from the approved file frontmatter:
- `to` — recipient email address
- `subject` — email subject (usually "Re: <original subject>")
- `thread_id` — Gmail thread ID for correct threading (may be empty for new thread)
- Draft body — read from the `## Draft Reply` section of the file body

Call the MCP `send_email` tool:
```
send_email(
    to=<to>,
    subject=<subject>,
    body=<draft body text>,
    reply_to_thread_id=<thread_id if present>
)
```

## post_linkedin Execution Detail

Read the post text from the `## Draft Content` section of the approved file.

Run via Bash:
```bash
uv --directory "G:/Hackathons/GIAIC_Hackathons/AI_Employee_Vault" run python -c "
import os; os.environ['DRY_RUN']='false'
from Scripts.linkedin_poster import LinkedInPoster
poster = LinkedInPoster()
result = poster.post_update('''<post text here>''')
print(result)
"
```

Note: LinkedIn poster reads the access token from `.env` or `.linkedin_token.json`.
Ensure `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` are set.

## discord_reply / whatsapp_reply Manual Execution

These platforms do not have auto-send capability at Silver tier. Instead:

1. Read the reply text from the approved file's `## Draft Reply` or `## Message` section
2. Display the text to the user with clear instructions:
   ```
   ACTION REQUIRED — Manual Discord/WhatsApp Reply
   Platform: Discord | Channel: <channel> | Author: <author>
   Reply text:
   ---
   <reply text>
   ---
   Please post this reply manually, then confirm here.
   ```
3. After user confirms, proceed with moving to Done/ and audit logging

## File Move Pattern

Since the file is already at `Approved/<filename>.md`, to move it to `Done/`:
1. Read the file content
2. Write it to `Done/<filename>.md` with updated frontmatter `status: done`
3. Note in the audit log that the file was moved from Approved/ to Done/

(The physical delete of the Approved/ file requires user permission — note this
to the user if they need to clean up the Approved/ folder manually.)

## Audit Log Entry

```json
{
  "timestamp": "<ISO 8601>",
  "action_type": "<action value>_executed",
  "actor": "ApprovalExecuting",
  "target": "<to / linkedin / discord channel / whatsapp contact>",
  "parameters": {
    "approved_file": "<filename>",
    "action": "<action>",
    "result": "<success | skipped_expired | manual_required>"
  },
  "approval_status": "approved",
  "approved_by": "human",
  "result": "<success | skipped_expired | manual_required>"
}
```

## Expiry Handling

- Check `expires` field against current UTC time
- If expired: log `result: skipped_expired`, notify user, do NOT execute
- User must re-create the approval request via `hitl-approval-requesting`

## Rules

1. Never execute an action without first confirming the file is in `Approved/`
   (not just `Pending_Approval/`).
2. Always check the `expires` field before executing — stale approvals must not run.
3. For `discord_reply` and `whatsapp_reply`, always present the reply text to
   the user and wait for manual confirmation before logging success.
4. Never modify the original source file in `Needs_Action/` — only the approved copy.
5. One execution per approved file — do not batch multiple actions from one file.
6. After all executions, invoke `dashboard-updating`.
