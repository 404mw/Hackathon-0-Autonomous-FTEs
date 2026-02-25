---
name: plan-generating
description: >
  Creates PLAN_*.md files with checkboxes, dependencies, and approval flags.
  Use when an action item needs multi-step work — triggered after triage or
  when the user requests a plan for a task.
allowed-tools: Read, Write, Glob, Grep
---

# Plan Generating

Creates structured plan files in `Plans/` for action items that require multi-step work.

## When to Invoke

- After `email-triaging` or `file-processing` identifies an item needing multi-step action
- After `vault-triaging` routes an item that requires planning
- When the user explicitly asks to create a plan for a task
- When any skill determines an action requires more than one step

## Plan Generation Flow

1. **Read** the source item (from `Needs_Action/` or as provided)
2. **Determine objective** — what is the desired end state?
3. **Break down into steps** — each step should be a single, concrete action
4. **Identify approval gates** — which steps involve external actions (email, payment, posting)?
5. **Set dependencies** — which steps must happen before others?
6. **Write** the plan file to `Plans/`
7. **Log** via `audit-logging`

## Plan File Location

```
Plans/PLAN_<slug>.md
```

Slug is derived from the source item:
- `EMAIL_18d3f2a1b4c.md` → `PLAN_email_18d3f2a1b4c.md`
- `FILE_report.pdf.md` → `PLAN_file_report_pdf.md`
- `WHATSAPP_client_a_2026-02-25.md` → `PLAN_whatsapp_client_a_2026_02_25.md`
- Manual task "fix login bug" → `PLAN_fix_login_bug.md`

## Plan Template

```markdown
---
type: plan
status: pending
priority: <priority from source item or assessed>
created: <ISO 8601 timestamp>
source: <path to source file, or "manual">
---

## Objective
<1-sentence description of what needs to happen>

## Context
- **Source:** <watcher type or manual>
- **From:** <sender/origin if applicable>
- **Received:** <original timestamp>
- **Summary:** <brief content summary>

## Steps
- [ ] <step 1>
- [ ] <step 2>
- [ ] <step 3> (REQUIRES APPROVAL)

## Approval Required
<Yes/No — if yes, list which steps need HITL approval>

## Related Files
- Source: `<path to source file>`
```

## Step Writing Guidelines

- Each step should be **one concrete action** (not "research and implement")
- Use imperative verbs: "Draft reply", "Generate invoice", "Move file to Done/"
- Mark steps that involve external actions with `(REQUIRES APPROVAL)`:
  - Sending emails
  - Making payments
  - Posting to social media
  - Deleting files outside the vault
  - Any action listed in `Company_Handbook.md` as requiring approval
- Include a final step to move the source item to `Done/` after completion

## Priority Inheritance

The plan inherits priority from its source item. If no source priority exists:

| Condition | Priority |
|-----------|----------|
| Involves payment or invoice | high |
| Has a deadline within 48 hours | urgent |
| Routine task, no deadline | normal |
| Informational or archival | low |

## Rules

1. One plan per source item. Never merge multiple items into one plan.
2. Plans must be self-contained — anyone reading the plan should understand what to do without checking other files.
3. Never auto-execute plan steps. Plans are proposals awaiting processing.
4. If a step requires information not available in the source item, add a step: "Clarify with user: <what's missing>."
5. Always include the source file path in `Related Files` for traceability.
6. After creating a plan, invoke `audit-logging`.
7. After creating a plan, invoke `dashboard-updating`.
