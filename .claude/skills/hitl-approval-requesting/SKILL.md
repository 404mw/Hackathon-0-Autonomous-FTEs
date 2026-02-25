---
name: hitl-approval-requesting
description: >
  Creates human-in-the-loop approval request files in Pending_Approval/.
  Use whenever the AI Employee needs to perform a sensitive action: sending
  emails, making payments, posting to social media, deleting files, or any
  action crossing the permission boundaries in Company_Handbook.md.
allowed-tools: Read, Write, Glob, Grep
---

# HITL Approval Requesting

Creates structured approval request files in `Pending_Approval/` for any action that requires human sign-off before execution.

## When to Invoke

Always create an approval request before:

- Sending any email (to new contacts, bulk, or with attachments)
- Making any payment (all amounts to new payees, > $100 to known payees)
- Posting to any social media platform
- Replying to DMs on any platform
- Deleting or moving files outside the vault
- Any action flagged in `Company_Handbook.md` as requiring approval

Refer to the permission boundaries:

| Action | Auto-Approve | Always Require Approval |
|--------|-------------|------------------------|
| Email replies | To known contacts only | New contacts, bulk sends |
| Payments | < $50 recurring to known payees | All new payees, > $100 |
| Social media | Scheduled posts (pre-approved) | Replies, DMs |
| File operations | Create, read within vault | Delete, move outside vault |

## File Location & Naming

```
Pending_Approval/<ACTION>_<target>_<YYYY-MM-DD>.md
```

Examples:
- `Pending_Approval/EMAIL_client_a_2026-02-25.md`
- `Pending_Approval/PAYMENT_Client_B_2026-02-25.md`
- `Pending_Approval/SOCIAL_linkedin_post_2026-02-25.md`

## Approval File Template

Every approval request must use this structure:

```markdown
---
type: approval_request
action: <email_send | email_reply | payment | social_post | social_reply | file_delete | file_move | other>
status: pending
priority: <low | normal | high | urgent>
created: <ISO 8601 timestamp>
expires: <ISO 8601 timestamp, 24 hours after created>
source_plan: <path to Plan file that triggered this, or "direct">
---

## Action Summary
<1-2 sentence plain-language description of what will happen if approved>

## Details
<Action-specific details in a readable format:>
<- For emails: to, subject, body summary, attachments>
<- For payments: amount, recipient, reference, bank details (masked)>
<- For social posts: platform, content preview, scheduled time>

## To Approve
Move this file to `/Approved/` folder.

## To Reject
Move this file to `/Rejected/` folder.
```

## Rules

1. Never execute a sensitive action without a corresponding approval file.
2. Set `expires` to 24 hours after `created`. Expired approvals must not be executed — create a new one.
3. Mask sensitive data: show last 4 digits of bank accounts, never include full credentials.
4. If the action originated from a Plan file, link it in `source_plan`.
5. One approval file per action. Do not batch multiple actions into one file.
6. After creating the approval file, invoke `audit-logging` to log the request.
7. After creating the file, notify the user that an action is pending their approval in `Pending_Approval/`.
