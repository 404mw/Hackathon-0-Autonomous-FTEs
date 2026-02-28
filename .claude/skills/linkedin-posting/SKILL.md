---
name: linkedin-posting
description: Generates and routes LinkedIn post drafts for human approval before publishing. Use when the user requests a LinkedIn post, when a plan step requires a LinkedIn update, or when outreach or thought-leadership content is needed.
allowed-tools: Read, Write, Glob, Grep
---

# LinkedIn Posting

Generates a LinkedIn post draft and routes it through the HITL approval flow.
Never calls the LinkedIn API directly — always goes through `Pending_Approval/` first.

## When to Invoke

- When the user requests a LinkedIn post or update
- When a `PLAN_*.md` step calls for LinkedIn outreach or content
- When the scheduled `LINKEDIN_POST_SCHEDULE` days are triggered by the orchestrator

## Posting Flow

1. **Gather context** — read `Business_Goals.md` and `Company_Handbook.md` for
   brand voice, objectives, and prohibited content
2. **Generate draft** — write a professional LinkedIn post following the guidelines below
3. **Create approval request** — write `LINKEDIN_POST_<slug>_<YYYY-MM-DD>.md` to
   `Pending_Approval/`
4. **Log and update** — invoke `audit-logging` and `dashboard-updating`
5. **Await human approval** — do NOT proceed further until the file is in `Approved/`

## Post Generation Guidelines

- **Tone:** professional, value-driven, first-person
- **Length:** 150–300 words for best reach on LinkedIn
- **Opening hook:** first 2 lines must stand alone (visible before "see more")
- **Structure:** Hook → Context/Story → Value/Insight → Call to Action
- **Hashtags:** 3–5 relevant hashtags, placed at the end; no hashtag spam
- **No hard sells:** lead with value, not promotion
- **No confidential data:** no client names, revenue figures, or unreleased project details

## Approval Request Format

Create `Pending_Approval/LINKEDIN_POST_<slug>_<YYYY-MM-DD>.md`:

```yaml
---
type: approval_request
status: pending
priority: normal
created: <ISO 8601>
source: linkedin-posting skill
action: post_linkedin
target: linkedin_post
requires_approval: true
approved_by:
---
```

```markdown
# LinkedIn Post Draft — <slug>

**Platform:** LinkedIn
**Action:** Publish post
**Requires Approval:** Yes

## Draft Content

<post text here>

## Suggested Hashtags

<3-5 hashtags>

## Approval Checklist

- [ ] Tone matches Company_Handbook.md guidelines
- [ ] No confidential information disclosed
- [ ] Hashtags are relevant and professional (3-5 max)
- [ ] Hook is compelling in the first 2 lines
- [ ] Post length is 150–300 words

## After Approval

Move this file to `Approved/` to trigger the `approval-executing` skill,
which will call `Scripts/linkedin_poster.py` to publish.
```

## Rules

1. Never call the LinkedIn API without going through `Pending_Approval/` first.
2. Never include client names, financial figures, or confidential project details.
3. Always check `Company_Handbook.md` for brand voice and prohibited content.
4. After creating the approval request, invoke `audit-logging` and `dashboard-updating`.
5. One post per approval request — do not batch multiple drafts into a single file.