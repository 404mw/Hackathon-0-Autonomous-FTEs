---
name: audit-logging
description: >
  Logs every AI action to Logs/YYYY-MM-DD.json in a structured JSON format.
  Use after any vault write, external action, approval flow, file move, or
  error event. Ensures a complete audit trail for all AI Employee activity.
allowed-tools: Read, Write, Glob, Grep
---

# Audit Logging

Log every AI action to `Logs/YYYY-MM-DD.json`. This skill is invoked after every meaningful action the AI Employee takes.

## When to Invoke

- After writing, moving, or deleting any file in the vault
- After any MCP action (email send, social post, payment, etc.)
- After creating or processing an approval request
- After any error or failed operation
- After Dashboard.md is updated

## Log File Location

```
Logs/YYYY-MM-DD.json
```

One file per day. Each file contains a JSON array of log entries. If the file already exists, read it, parse the array, append the new entry, and write back. If it does not exist, create it with a new array containing the single entry.

## Log Entry Schema

Every entry must include all of these fields:

```json
{
  "timestamp": "<ISO 8601, e.g. 2026-02-25T14:30:00Z>",
  "action_type": "<one of: file_create, file_move, file_delete, email_send, email_draft, social_post, payment, approval_request, approval_execute, dashboard_update, plan_create, triage, briefing_generate, error, watcher_event>",
  "actor": "<who performed it: claude_code | gmail_watcher | whatsapp_watcher | filesystem_watcher | orchestrator | human>",
  "target": "<what was acted upon: file path, email address, social platform, etc.>",
  "parameters": {},
  "approval_status": "<not_required | pending | approved | rejected>",
  "approved_by": "<human | auto | n/a>",
  "result": "<success | failure | partial>",
  "error_detail": "<null or error message string if result is failure>"
}
```

## Rules

1. Never skip logging. Every action gets a log entry, even if the action failed.
2. Never log secrets, credentials, tokens, or full email bodies. Log subjects, filenames, and summaries only.
3. `parameters` should contain enough context to understand what happened without including sensitive data.
4. If `Logs/` folder does not exist, create it before writing.
5. Retain logs for minimum 90 days. Never delete log files without explicit user instruction.

## Example

After sending an approved email:

```json
{
  "timestamp": "2026-02-25T10:45:00Z",
  "action_type": "email_send",
  "actor": "claude_code",
  "target": "client_a@email.com",
  "parameters": {
    "subject": "January 2026 Invoice - $1,500",
    "has_attachment": true,
    "source_approval_file": "Approved/EMAIL_invoice_client_a.md"
  },
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success",
  "error_detail": null
}
```
