---
name: dashboard-updating
description: >
  Refreshes Dashboard.md with current vault state including system status,
  pending actions, recent activity, and financial summary. Use after any
  vault state change, completed action, or when the user requests a status
  overview. Single-writer rule: only the local agent writes Dashboard.md.
allowed-tools: Read, Write, Glob, Grep
---

# Dashboard Updating

Refreshes `Dashboard.md` at the vault root with the current state of the entire AI Employee system.

## When to Invoke

- After any file is moved to `Done/`
- After any new item lands in `Needs_Action/`
- After an approval is processed (approved or rejected)
- After a Plan is created or completed
- After financial data changes in `Accounting/`
- When the user asks for a status update
- At the start of any scheduled operation (daily briefing, etc.)

## Data Sources

Scan these locations to build the dashboard:

| Section | Source |
|---------|--------|
| System Status | Check if watcher PIDs are alive (if available), otherwise report "Unknown" |
| Pending Actions | Count and list files in `Needs_Action/`, `Plans/`, `Pending_Approval/` |
| In Progress | Count and list files in `In_Progress/` |
| Recent Activity | Read last 10 entries from today's `Logs/YYYY-MM-DD.json` |
| Financial Summary | Read `Accounting/` files for MTD revenue, pending invoices, pending payments |
| Active Projects | Read `Business_Goals.md` for project list and deadlines |

## Dashboard.md Template

```markdown
---
last_updated: <ISO 8601 timestamp>
---

# AI Employee Dashboard

## System Status
| Component | Status | Last Seen |
|-----------|--------|-----------|
| Orchestrator | <Running/Stopped/Unknown> | <timestamp or N/A> |
| Gmail Watcher | <Running/Stopped/Unknown> | <timestamp or N/A> |
| WhatsApp Watcher | <Running/Stopped/Unknown> | <timestamp or N/A> |
| File Watcher | <Running/Stopped/Unknown> | <timestamp or N/A> |

## Pending Actions
| File | Type | Priority | Age |
|------|------|----------|-----|
<list items from Needs_Action/ and Pending_Approval/>

> <total count> items pending.

## In Progress
<list items from In_Progress/, or "No items in progress.">

## Recent Activity
<last 10 log entries, formatted as a readable list>

## Financial Summary
| Metric | Value |
|--------|-------|
| MTD Revenue | <from Accounting/> |
| Pending Invoices | <count from Invoices/ with status pending> |
| Pending Payments | <count from Pending_Approval/ with action: payment> |

## Active Projects
<from Business_Goals.md, show name, due date, and budget>
```

## Rules

1. **Single-writer rule:** Only the local agent writes `Dashboard.md`. Cloud agents write updates to `Updates/` for merge.
2. Always update the `last_updated` frontmatter timestamp.
3. If a data source is missing or empty (e.g., no `Accounting/` folder yet), show "N/A" — never error out.
4. Keep the dashboard concise. Summarize, don't dump raw data.
5. After updating, invoke `audit-logging` with `action_type: dashboard_update`.
6. Never include sensitive data (amounts > summary level, credentials, full email bodies) in the dashboard.
