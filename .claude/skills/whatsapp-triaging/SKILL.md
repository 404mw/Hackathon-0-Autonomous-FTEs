---
name: whatsapp-triaging
description: Classifies WhatsApp messages by priority and intent, suggests concrete next actions, and routes to plan-generating or hitl-approval-requesting as needed. Use when WHATSAPP_*.md files appear in Needs_Action/ from the WhatsApp watcher or manual drops.
allowed-tools: Read, Write, Glob, Grep
---

# WhatsApp Triaging

Processes `WHATSAPP_*.md` files in `Needs_Action/`, classifies them by intent and
priority, and routes them to the appropriate next step.

## When to Invoke

- When a `WHATSAPP_*.md` file appears in `Needs_Action/`
- When `vault-triaging` identifies an item with the `WHATSAPP_` prefix
- When the user asks to process pending WhatsApp messages

## Triage Flow

For each `WHATSAPP_*.md` file:

1. **Read** the file: frontmatter fields (sender, priority, message_preview) + body
2. **Check** `Company_Handbook.md` for any sender-specific rules
3. **Classify intent** into one of:
   - `invoice_request` — sender references an invoice or payment
   - `meeting_request` — scheduling or availability request
   - `action_required` — sender expects a specific response or deliverable
   - `urgent_help` — distress signal, needs immediate attention
   - `general_enquiry` — question with no urgency
   - `spam_or_noise` — irrelevant, unsolicited, or duplicate
4. **Assess priority** (may override the watcher's pre-set priority):
   - Contains "urgent", "asap", "emergency" → `urgent`
   - Known client + action required → `high`
   - Invoice or payment mention → `high`
   - Unknown sender + no action keywords → `low`
5. **Update frontmatter** in place — change `status` to `in_progress`
6. **Route** based on intent:
   - `spam_or_noise` → archive to `Done/` directly; no plan needed
   - `invoice_request` → invoke `plan-generating` for an invoice plan
   - `action_required` / `urgent_help` → invoke `hitl-approval-requesting` for
     a WhatsApp reply approval (action: `whatsapp_reply`)
   - `meeting_request` → invoke `plan-generating` for scheduling plan
   - `general_enquiry` → create a short plan with suggested reply text
7. **Log** via `audit-logging`; **update** `dashboard-updating`

## Updated Frontmatter

```yaml
---
type: whatsapp
status: in_progress
priority: <reassessed priority>
created: <original>
source: whatsapp_watcher
intent: <classified intent>
contact: "<sender>"
suggested_action: <next step>
---
```

## Priority × Intent Decision Table

| Intent | Known Contact | Priority | Action |
|--------|--------------|----------|--------|
| urgent_help | any | urgent | HITL reply approval immediately |
| invoice_request | yes | high | Invoice plan |
| action_required | yes | high | HITL reply approval |
| action_required | no | normal | Plan with human-review step |
| meeting_request | any | normal | Scheduling plan |
| general_enquiry | any | low | Draft reply in plan |
| spam_or_noise | any | low | Archive to Done/ |

## Rules

1. Never auto-reply to WhatsApp messages. All replies must go through `hitl-approval-requesting`.
2. Always check `Company_Handbook.md` before assigning priority to a known client.
3. If intent is ambiguous, default to `action_required` with `normal` priority.
4. Do not merge multiple WHATSAPP files into a single plan.
5. After processing, invoke `audit-logging` and `dashboard-updating`.