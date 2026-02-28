---
name: email-drafting
description: Drafts email replies in the owner's voice using source email context and Company_Handbook.md tone rules. Creates an approval request in Pending_Approval/ with full send parameters. Use when a plan step requires an email reply or when the user explicitly requests a draft.
allowed-tools: Read, Write, Glob, Grep
---

# Email Drafting

Reads a source email, drafts a professional reply matching the owner's voice,
and writes an approval request to `Pending_Approval/` for human review before
any sending occurs.

## When to Invoke

- When a `PLAN_*.md` step calls for an email reply
- When `email-triaging` classifies an email as `action_required`
- When the user explicitly asks to draft a reply to a specific email
- When a client email requires a formal written response

## Drafting Flow

1. **Read** the source `EMAIL_*.md` file from `Needs_Action/`:
   - Sender name and address
   - Subject line
   - Date received
   - Key ask or question (extracted from body/preview — do NOT re-read
     the full body; summarise from the preview or previously triaged fields)
2. **Read** `Company_Handbook.md`:
   - Owner's communication style
   - Client-specific rules (if sender is a known client)
   - Tone guidelines (formal / semi-formal / casual)
3. **Draft the reply**:
   - Match the sender's register — reply formally to formal emails
   - Be concise: answer the specific ask, nothing more
   - Do not include boilerplate filler ("Hope this finds you well...")
   - End with a clear next step or question if required
   - Length: 50–200 words for typical replies; longer only if complexity demands
4. **Create approval request** at:
   ```
   Pending_Approval/EMAIL_SEND_<slug>_<YYYY-MM-DD>.md
   ```
   where `<slug>` matches the source email's message ID or subject slug
5. **Log** via `audit-logging`; **notify** user that draft is pending approval

## Approval Request Format

```yaml
---
type: approval_request
action: send_email
status: pending
priority: <inherited from source email>
created: <ISO 8601>
expires: <ISO 8601, 24 hours after created>
source_plan: <path to PLAN_*.md if applicable, else "direct">
to: "<recipient email>"
subject: "Re: <original subject>"
thread_id: "<gmail thread ID from source EMAIL_*.md frontmatter>"
---
```

```markdown
## Draft Reply

<full draft email body here>

## Context

- **Original email:** `<path to EMAIL_*.md>`
- **Sender:** <name> <<email>>
- **Received:** <date>
- **Original ask:** <1-sentence summary>

## Approval Checklist

- [ ] Tone matches Company_Handbook.md guidelines
- [ ] Draft answers the specific ask
- [ ] No confidential information included inappropriately
- [ ] Subject line is correct (Re: <original subject>)

## After Approval

Move this file to `Approved/`. The `approval-executing` skill will call
the `send_email` MCP tool using the frontmatter send parameters.
```

## Tone Guidelines (from Company_Handbook.md)

- **Known client:** Semi-formal. By name. Responsive and direct.
- **New contact:** Formal. Professional. No first-name basis until established.
- **Internal / user to self:** Casual shorthand is fine.
- **Invoice / payment topic:** Formal, factual, reference numbers.
- **Complaint:** Empathetic, calm, solution-focused.

## Rules

1. Never send an email directly — always write to `Pending_Approval/` first.
2. Always include the `thread_id` in frontmatter so the email threads correctly
   in Gmail when sent via the MCP server.
3. Do not re-read the full original email body — use the `message_preview` or
   previously extracted summary to avoid unnecessary data exposure.
4. Set `expires` to 24 hours after creation. Expired drafts must not be sent.
5. If the correct tone or response is unclear, draft two versions and add a note
   asking the owner to pick one before approving.
6. After creating the approval request, invoke `audit-logging`.