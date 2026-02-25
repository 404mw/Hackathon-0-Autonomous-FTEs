---
name: vault-triaging
description: >
  Reads, classifies, and routes items from Needs_Action/ into Plans/.
  Use when new files appear in Needs_Action/ from any watcher (Gmail,
  WhatsApp, filesystem) or manual drops. Determines item type, priority,
  and required actions, then creates a corresponding Plan file.
allowed-tools: Read, Write, Glob, Grep
---

# Vault Triaging

Processes all unhandled items in `Needs_Action/`, classifies them, and creates structured Plan files in `Plans/`.

## When to Invoke

- When new `.md` files appear in `Needs_Action/`
- When the orchestrator triggers a triage cycle
- When the user asks to process pending items
- Periodically as part of the main reasoning loop

## Triage Flow

For each file in `Needs_Action/`:

1. **Read** the file and its YAML frontmatter
2. **Classify** by type using the filename prefix and frontmatter `type` field:
   - `EMAIL_*` → email triage
   - `WHATSAPP_*` → WhatsApp triage
   - `FILE_*` → file processing
   - Unknown prefix → manual review
3. **Assess priority** based on:
   - Frontmatter `priority` field if present
   - Keywords in content: "urgent", "asap", "deadline", "payment", "invoice" → high
   - Sender importance (check against known contacts in `Company_Handbook.md` if available)
   - Age: items older than 24 hours get priority bumped
4. **Determine actions** needed (reply, forward, generate invoice, schedule, etc.)
5. **Create a Plan file** in `Plans/`
6. **Log** the triage via `audit-logging`

## Plan File Output

For each triaged item, create:

```
Plans/PLAN_<slug_from_source>.md
```

Example: `Needs_Action/EMAIL_18d3f2a1b4c.md` → `Plans/PLAN_email_18d3f2a1b4c.md`

### Plan Template

```markdown
---
type: plan
status: pending
priority: <assessed priority>
created: <ISO 8601 timestamp>
source: <path to original file in Needs_Action/>
---

## Objective
<1-sentence description of what needs to happen>

## Context
- **Source:** <watcher type that created it>
- **From:** <sender if applicable>
- **Received:** <original timestamp>
- **Summary:** <brief content summary>

## Steps
- [ ] <step 1>
- [ ] <step 2>
- [ ] <step 3 — mark with (REQUIRES APPROVAL) if sensitive>

## Approval Required
<Yes/No. If yes, list which steps need HITL approval>

## Related Files
- Source: `<path to Needs_Action file>`
```

## Classification Rules

| Prefix | Type | Default Priority | Typical Actions |
|--------|------|-----------------|-----------------|
| `EMAIL_` | email | normal | Reply, forward, archive, extract action items |
| `WHATSAPP_` | whatsapp | high | Reply, escalate, create invoice, schedule meeting |
| `FILE_` | file_drop | low | Categorize, extract data, move to appropriate folder |
| Unknown | manual | normal | Flag for human review |

## Priority Escalation

| Condition | Action |
|-----------|--------|
| Contains "urgent", "asap", "emergency" | Set priority to `urgent` |
| Contains "invoice", "payment", "deadline" | Set priority to `high` |
| From unknown sender | Set priority to `normal`, flag for review |
| Item age > 24 hours and still in `Needs_Action/` | Bump priority one level |

## Rules

1. Never delete source files from `Needs_Action/` during triage. They stay until the plan is fully executed and moved to `Done/`.
2. One Plan file per source item. Do not merge multiple items into one plan.
3. If classification is ambiguous, set priority to `normal` and add a step: "Human review required — unclear intent."
4. Always check `Company_Handbook.md` for sender-specific rules before assigning actions.
5. After triage is complete, invoke `dashboard-updating` to reflect the new plans.
6. After triage, invoke `audit-logging` for each item triaged.
