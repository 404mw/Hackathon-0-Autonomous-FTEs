---
name: discord-triaging
description: Classifies Discord messages (@mentions and DMs) by intent, routes actionable items to plan-generating or hitl-approval-requesting, and archives noise directly to Done/. Use when DISCORD_*.md files appear in Needs_Action/.
allowed-tools: Read, Write, Glob, Grep
---

# Discord Triaging

Processes `DISCORD_*.md` files in `Needs_Action/`, classifies them by intent,
and routes them to the correct next step.

## When to Invoke

- When a `DISCORD_*.md` file appears in `Needs_Action/`
- When `vault-triaging` identifies an item with the `DISCORD_` prefix
- When the user asks to process pending Discord messages

## Triage Flow

For each `DISCORD_*.md` file:

1. **Read** the file: frontmatter (author, guild, channel, trigger, priority,
   message_preview) + full message content
2. **Check** `Company_Handbook.md` for any sender-specific rules
3. **Classify intent** into one of:
   - `support_request` — user needs help with a product, service, or technical issue
   - `lead_or_inquiry` — potential client asking about services or pricing
   - `feedback` — comment or review about existing work
   - `collaboration` — partnership or joint-work proposal
   - `action_required` — a specific task or deliverable is being requested
   - `noise` — greetings, spam, off-topic, bot commands, or test messages
4. **Assess priority** (may override the watcher's pre-set priority):
   - Contains "urgent", "asap", "emergency" → `urgent`
   - Known contact + action required → `high`
   - New lead or client inquiry → `high`
   - Feedback or collaboration → `normal`
   - Noise → `low`
5. **Route** based on intent:
   - `noise` → archive directly to `Done/`; no plan or reply needed
   - `support_request` → invoke `plan-generating` for a support response plan;
     invoke `hitl-approval-requesting` (action: `discord_reply`) if a reply is due
   - `lead_or_inquiry` → invoke `plan-generating`; include a reply draft step
   - `feedback` → acknowledge in plan; archive to `Done/` if no further action
   - `collaboration` → invoke `plan-generating` with evaluation steps
   - `action_required` → invoke `hitl-approval-requesting` (action: `discord_reply`)
6. **Update frontmatter** in place — change `status` to `in_progress`
7. **Log** via `audit-logging`; **update** `dashboard-updating`

## Updated Frontmatter

```yaml
---
type: discord
status: in_progress
priority: <reassessed priority>
created: <original>
source: discord_watcher
trigger: <mention | dm>
intent: <classified intent>
guild: "<server>"
channel: "<channel>"
author: "<username>"
suggested_action: <next step>
---
```

## Priority × Intent Decision Table

| Intent | Priority | Routing |
|--------|----------|---------|
| support_request | high | Plan + HITL reply approval |
| lead_or_inquiry | high | Plan + HITL reply approval |
| action_required | high | HITL reply approval immediately |
| collaboration | normal | Plan with evaluation steps |
| feedback | normal | Plan (or Done/ if no action needed) |
| noise | low | Archive to Done/ |

## Note on Discord Replies

Discord replies must go through `hitl-approval-requesting` with
`action: discord_reply`. The `approval-executing` skill handles posting
the reply manually — there is no auto-send capability at this tier.

## Rules

1. Never auto-reply to Discord messages. All replies require HITL approval.
2. DM messages (trigger: dm) should generally be treated as higher priority
   than server @mentions from the same author.
3. If a message is from a server the owner has not configured, treat as `normal`.
4. Noise should be archived without creating a plan — keep `Plans/` clean.
5. After processing, invoke `audit-logging` and `dashboard-updating`.