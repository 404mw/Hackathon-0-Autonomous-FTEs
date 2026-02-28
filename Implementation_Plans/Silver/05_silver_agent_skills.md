# Silver Plan 05 — Silver Agent Skills

## Overview

Four new Agent Skills to add for Silver tier, plus one custom skill for
Discord triaging (not in the original suggested list but required by our
Discord watcher). All live in `.claude/skills/`.

## Skills to Create

### 1. `whatsapp-triaging`

**Trigger:** `WHATSAPP_*.md` appears in `Needs_Action/`

**Responsibility:**
- Read the WHATSAPP file frontmatter + message preview
- Classify priority (urgent / normal / low) based on keywords and tone
- Detect intent: invoice request, urgent help, general enquiry, spam
- Suggest 2-3 concrete next actions
- Update file status to `in_progress`
- Route to `Plans/` via plan-generating skill if multi-step work needed
- Create HITL approval request if a reply is required

**Output:** Updates the WHATSAPP_*.md status + may create a PLAN_*.md

---

### 2. `discord-triaging`

**Trigger:** `DISCORD_*.md` appears in `Needs_Action/`

**Responsibility:**
- Same classification logic as whatsapp-triaging
- Detect if message is a support request, question, lead, or noise
- If actionable: create PLAN_*.md and/or HITL approval for reply
- If noise: move directly to Done/

**Output:** Updates DISCORD_*.md status + may create PLAN_*.md

---

### 3. `email-drafting`

**Trigger:** A Plan step requires an email reply, or user requests a draft

**Responsibility:**
- Read the source email (EMAIL_*.md) for context
- Read Company_Handbook.md for tone rules
- Draft a reply matching the owner's voice and handbook guidelines
- Write the draft to `Pending_Approval/EMAIL_SEND_<slug>_<date>.md`
- Include the draft body + send parameters (to, subject, thread_id) in
  frontmatter so `approval-executing` can send it directly

**Frontmatter of approval file:**
```yaml
---
type: approval_request
action: send_email
status: pending
priority: normal
created: <ISO 8601>
to: "<recipient>"
subject: "<subject>"
thread_id: "<gmail thread id>"
expires: <24h from created>
---
```

---

### 4. `linkedin-posting`

**Trigger:** Scheduled (Mon/Wed/Fri) or manual user request

**Responsibility:**
- Read `Business_Goals.md` for current objectives and messaging
- Read recent `Done/` items for talking points
- Generate a LinkedIn post (150-300 words) in owner's professional voice
- Create `Pending_Approval/LINKEDIN_POST_<date>.md` with post body
- After approval, `approval-executing` calls `linkedin_poster.py`

**Post quality rules:**
- No hashtag spam (max 5 relevant hashtags)
- No AI-sounding filler phrases ("In today's fast-paced world...")
- Professional but human tone
- Always ends with a question or CTA

---

### 5. `approval-executing`

**Trigger:** A file appears in `Approved/`

**Responsibility:**
- Read the approved file's `action` frontmatter field
- Route to the correct executor:
  - `send_email` → call MCP `send_email` tool
  - `linkedin_post` → call `linkedin_poster.py`
  - `discord_reply` → call MCP discord tool (future)
  - `whatsapp_reply` → log as manual action (no auto-send)
- Move source file from `Approved/` to `Done/`
- Write audit log entry
- Update Dashboard.md

---

## Steps

- [x] 1. Create `.claude/skills/whatsapp-triaging/SKILL.md`
- [x] 2. Create `.claude/skills/discord-triaging/SKILL.md`
- [x] 3. Create `.claude/skills/email-drafting/SKILL.md`
- [x] 4. Create `.claude/skills/linkedin-posting/SKILL.md` (done in Plan 03)
- [x] 5. Create `.claude/skills/approval-executing/SKILL.md`
- [x] 6. Updated `vault-triaging` description to reference all Silver platform skills
- [ ] 7. Test each skill with a sample file in Needs_Action/
- [ ] 8. Update Dashboard.md to reflect Silver skills are active

## Files Created

- `.claude/skills/whatsapp-triaging/SKILL.md`
- `.claude/skills/discord-triaging/SKILL.md`
- `.claude/skills/email-drafting/SKILL.md`
- `.claude/skills/linkedin-posting/SKILL.md`
- `.claude/skills/approval-executing/SKILL.md`

## Issues & Resolutions

### Issue 1 — Skill YAML linter rejects `>` block scalars in `description`

**Symptom:** IDE linter reports "Unexpected indentation" and "Attribute not
supported" errors for every continuation line of a `description: >` block scalar.

**Root cause:** The Claude Code skill file YAML parser only accepts `description`
as an inline single-line string. The `>` folded block scalar syntax (multi-line
indented) is not supported, even though standard YAML parsers handle it correctly.

**Fix:** Changed all `description: >\n  <lines>` in every skill created this
session to `description: <single-line string>`. Descriptions were condensed to
fit on one line without changing their meaning.

_(Document bugs here as encountered.)_
