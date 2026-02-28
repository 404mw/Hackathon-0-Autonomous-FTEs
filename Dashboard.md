---
type: dashboard
status: active
last_updated: 2026-02-28T17:22:00Z
---

# Dashboard

Real-time system status for the AI Employee vault. **Single-writer rule:** only the local agent updates this file.

## System Status

| Component | Status | Last Seen |
|-----------|--------|-----------|
| Orchestrator | Error | 2026-02-28T15:33:23Z |
| Gmail Watcher | Unknown | 2026-02-26T15:41:43Z |
| Discord Watcher | Online | 2026-02-28T17:02:49Z |
| WhatsApp Watcher | Not configured | — |
| Filesystem Watcher | Unknown | — |

## Pending Actions

| File | Type | Priority | Age |
|------|------|----------|-----|
| `Needs_Action/EMAIL_19c9a9c6c034bf97.md` | email | **high** | 2 days |
| `Needs_Action/DISCORD_digital-fte_1476671272166625301.md` | discord | **high** | 2 days |
| `Needs_Action/DISCORD_digital-fte_1477350340994138225.md` | discord | normal | < 1 hour |

> **3 items in Needs_Action.** 3 plans created and pending execution.

## Pending Approvals

| File | Action | Priority | Waiting Since |
|------|--------|----------|---------------|
| `Pending_Approval/EMAIL_nationswarriorrr_2026-02-26.md` | Email reply to nationswarriorrr@gmail.com | **high** | 2026-02-28T17:20:00Z |
| `Pending_Approval/DISCORD_REPLY_digital-fte_1476671272166625301_2026-02-28.md` | Discord reply to msg 1476671272166625301 | **high** | 2026-02-28T17:20:01Z |
| `Pending_Approval/DISCORD_REPLY_digital-fte_1477350340994138225_2026-02-28.md` | Discord reply to msg 1477350340994138225 | normal | 2026-02-28T17:20:02Z |

> **3 items awaiting your approval.** Move to `Approved/` to execute or `Rejected/` to discard.

## In Progress

No items in progress.

## Recent Activity

| Timestamp | Action | Actor | Result |
|-----------|--------|-------|--------|
| 2026-02-28T17:20:02Z | approval_request — Discord reply (test run msg) | claude_code | success |
| 2026-02-28T17:20:01Z | approval_request — Discord reply (first msg) | claude_code | success |
| 2026-02-28T17:20:00Z | approval_request — email reply (refreshed, w/ Claude attribution) | claude_code | success |
| 2026-02-28T17:12:02Z | plan_create — DISCORD_1477350340994138225 | claude_code | success |
| 2026-02-28T17:12:01Z | plan_create — DISCORD_1476671272166625301 | claude_code | success |
| 2026-02-28T17:12:00Z | triage — EMAIL priority bump normal->high | claude_code | success |
| 2026-02-28T17:02:49Z | discord_message_detected — m.w. in #digital-fte | DiscordWatcher | success |
| 2026-02-28T15:33:23Z | send_email_executed — orchestrator smoke test | Orchestrator | **error** |

## Critical Alerts

> **[WARN] Orchestrator error:** Last execution at 2026-02-28T15:33:23Z returned error on smoke-test send. Check MCP email-send server / Gmail token (`gmail.send` scope required — re-run `Scripts/gmail_auth.py`).
>
> **[WARN] Gmail Watcher silent:** No new events since 2026-02-26T15:41:43Z. Confirm process is running.

## Financial Summary

| Metric | Value |
|--------|-------|
| MTD Revenue (Feb 2026) | — |
| Outstanding invoices | — |
| Pending payments | 0 |
| Software costs (this month) | — |

## Active Projects

| Project | Client | Due Date | Budget | Status |
|---------|--------|----------|--------|--------|
| _Example Project_ | _Client A_ | 2026-03-15 | $5,000 | In Progress |
