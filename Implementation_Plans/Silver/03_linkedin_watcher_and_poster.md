# Silver Plan 03 — LinkedIn Watcher & Poster

## Overview

Two distinct capabilities:

1. **LinkedIn Watcher** — polls LinkedIn for new messages/notifications and
   creates `LINKEDIN_*.md` files in `Needs_Action/`.
2. **LinkedIn Poster** — generates business posts for lead generation and
   routes them through the HITL approval flow before publishing.

## Approach

LinkedIn's API is heavily restricted (only approved Marketing Partners get
full access). For a hackathon, we use two strategies:

| Capability | Method | Rationale |
|------------|--------|-----------|
| Posting (UGC/share) | **LinkedIn API v2** (OAuth 2.0) | Official; requires app creation on LinkedIn Developer Portal. Scope: `w_member_social` |
| Reading messages | **Playwright** (web scraping) | LinkedIn messaging API is partner-only. Playwright automates LinkedIn.com |

## Part A — LinkedIn API Poster

### OAuth Flow

1. Create a LinkedIn App at `developer.linkedin.com`
2. Request `w_member_social` and `r_liteprofile` scopes
3. 3-legged OAuth: run `linkedin_auth.py` once to get `access_token`
4. Token stored in `.env` as `LINKEDIN_ACCESS_TOKEN`

### Posting Flow

```
linkedin-posting skill triggered
→ Generate post content (LLM)
→ Create HITL approval request in Pending_Approval/
→ User approves (moves file to Approved/)
→ approval-executing skill calls LinkedIn API POST /ugcPosts
→ Audit log updated
→ Dashboard updated
```

### API Endpoint

```
POST https://api.linkedin.com/v2/ugcPosts
Authorization: Bearer <access_token>

{
  "author": "urn:li:person:<person_id>",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": { "text": "<post_body>" },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
}
```

## Part B — LinkedIn Watcher (Playwright)

### Architecture

- Playwright persistent context, similar to WhatsApp watcher
- Logs into LinkedIn once (saves session to `.linkedin_session/`)
- Polls `/messaging/` page for unread conversation badges
- Extracts sender name + message preview
- Creates `LINKEDIN_<sanitised_sender>_<YYYY-MM-DD_HHMM>.md`

### File Naming

```
LINKEDIN_<sanitised_sender>_<YYYY-MM-DD_HHMM>.md
```

### Frontmatter

```yaml
---
type: linkedin
status: pending
priority: normal
created: <ISO 8601>
source: linkedin_watcher
sender: "<display name>"
message_preview: "<first 200 chars>"
---
```

## Steps

### LinkedIn Auth (one-time setup)
- [x] 1. Create LinkedIn App on developer.linkedin.com; request scopes
       (documented in `linkedin_auth.py` docstring — manual prerequisite)
- [x] 2. Created `Scripts/linkedin_auth.py` — standard OAuth 2.0 authorization
       code flow (not PKCE; client_secret is used); spins up local
       `http.server` on port 8080 to capture the callback automatically;
       fetches person URN via `/v2/userinfo` (OpenID Connect `sub` field);
       saves token to `Scripts/.linkedin_token.json`

### LinkedIn Poster
- [x] 3. Created `Scripts/linkedin_poster.py` — `LinkedInPoster` class (not
       a watcher; used by `approval-executing` skill)
       - `post_update(text: str) -> dict` — calls `POST /v2/ugcPosts`
       - Token loaded from env vars or `.linkedin_token.json`
       - No separate `get_person_urn()` call; URN stored at auth time
       - `dry_run=True` by default (inherits DRY_RUN env var)
- [x] 4. Created `linkedin-posting` skill in `.claude/skills/linkedin-posting/`

### LinkedIn Watcher
- [x] 5. Created `Scripts/linkedin_watcher.py` extending `BaseWatcher`:
       - `check_for_updates()` — Playwright persistent context; JS evaluate
         scrapes unread conversations with multi-selector fallbacks;
         dedup by sender→preview_hash (same MD5 pattern as WhatsApp)
       - `create_action_file()` — writes `LINKEDIN_*.md`; DRY_RUN pattern
         matches GmailWatcher/WhatsAppWatcher exactly (state inside each branch)
       - `_write_audit_log()` — same schema as other watchers
- [x] 6. First-run: headful launch for login (`input()` wait); headless
       on subsequent runs; session-expired detection with clear re-login message
- [x] 7. `.env.example` updated — LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET,
       LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN, LINKEDIN_SESSION_PATH,
       LINKEDIN_CHECK_INTERVAL, LINKEDIN_POST_SCHEDULE
- [ ] 8. Smoke test both paths

## Dependencies

```
playwright>=1.44       # already added for WhatsApp
requests>=2.32         # for LinkedIn API calls
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_ACCESS_TOKEN` | _(required)_ | OAuth bearer token |
| `LINKEDIN_PERSON_URN` | _(auto-fetched)_ | `urn:li:person:<id>` |
| `LINKEDIN_SESSION_PATH` | `Scripts/.linkedin_session` | Playwright session dir |
| `LINKEDIN_CHECK_INTERVAL` | `300` | Seconds between polls (5 min) |
| `LINKEDIN_POST_SCHEDULE` | `MON,WED,FRI` | Days to auto-trigger posting skill |
| `DRY_RUN` | `true` | Inherited from BaseWatcher |

## Files Created

- `Scripts/linkedin_auth.py`
- `Scripts/linkedin_poster.py`
- `Scripts/linkedin_watcher.py`
- `Scripts/.linkedin_session/` (runtime, gitignored)
- `Scripts/.linkedin_token.json` (runtime, gitignored)

## Issues & Resolutions

_(Document bugs here as encountered.)_
