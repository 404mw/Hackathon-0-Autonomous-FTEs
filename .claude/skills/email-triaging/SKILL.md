---
name: email-triaging
description: >
  Classifies email priority, extracts intent, and suggests actions per
  Company_Handbook.md rules. Use when EMAIL_*.md files appear in Needs_Action/
  from the Gmail watcher or manual drops.
allowed-tools: Read, Write, Glob, Grep
---

# Email Triaging

Processes `EMAIL_*.md` files in `Needs_Action/`, classifies them by priority and intent, and suggests next actions.

## When to Invoke

- When an `EMAIL_*.md` file appears in `Needs_Action/`
- When `vault-triaging` identifies an item with the `EMAIL_` prefix
- When the user asks to process pending emails

## Triage Flow

For each `EMAIL_*.md` file:

1. **Read** the file and its YAML frontmatter
2. **Extract** key fields:
   - Sender (name and email address)
   - Subject line
   - Date received
   - Body summary (do NOT log full body — summarize in 1-2 sentences)
3. **Classify intent** into one of:
   - `action_required` — sender expects a reply or deliverable
   - `invoice_request` — client is requesting or referencing an invoice
   - `meeting_request` — scheduling or calendar-related
   - `fyi` — informational, no response needed
   - `spam` — unsolicited or irrelevant
   - `urgent` — time-sensitive, requires immediate attention
4. **Assess priority** using these rules:
   - Known client (listed in `Company_Handbook.md`) → `high`
   - Contains "urgent", "asap", "deadline", "overdue" → `urgent`
   - Contains "invoice", "payment", "quote" → `high`
   - Contains "meeting", "schedule", "call" → `normal`
   - Unknown sender + no action keywords → `low`
   - Detected as spam → `low`
5. **Suggest actions** based on intent:
   - `action_required` → draft reply (route to `plan-generating`)
   - `invoice_request` → create invoice plan
   - `meeting_request` → propose times or confirm
   - `fyi` → archive to `Done/`
   - `spam` → archive to `Done/`, flag as spam
   - `urgent` → escalate, bump priority
6. **Update frontmatter** with classification results
7. **Log** via `audit-logging`

## Output

Update the `EMAIL_*.md` frontmatter in place:

```yaml
---
type: email
status: triaged
priority: <assessed priority>
created: <original timestamp>
source: gmail_watcher
intent: <classified intent>
sender: <sender email>
subject: <email subject>
suggested_action: <suggested next step>
---
```

## Classification Examples

| Subject | Sender | Intent | Priority | Suggested Action |
|---------|--------|--------|----------|------------------|
| "Invoice for January" | known client | invoice_request | high | Generate invoice |
| "Quick question about project" | known client | action_required | high | Draft reply |
| "Team lunch Friday?" | colleague | meeting_request | normal | Confirm or propose times |
| "Newsletter: Top 10 tips" | newsletter | fyi | low | Archive |
| "URGENT: Server is down" | known client | urgent | urgent | Escalate immediately |

## Rules

1. Never read or log the full email body. Work with subject, sender, and a brief summary only.
2. Always check `Company_Handbook.md` for sender-specific rules before classifying.
3. If intent is ambiguous, default to `action_required` with `normal` priority and flag for human review.
4. Emails classified as `urgent` should trigger a plan immediately — do not wait for the next triage cycle.
5. After triaging, invoke `audit-logging` for each email processed.
6. After all emails are triaged, invoke `dashboard-updating`.
