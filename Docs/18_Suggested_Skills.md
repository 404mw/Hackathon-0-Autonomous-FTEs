# Suggested Claude Agent Skills

All skills live in `.claude/skills/<name>/SKILL.md` following the [Agent Skills spec](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).
**Total: 19 skills** (4 cross-cutting + 3 Bronze + 4 Silver + 5 Gold + 4 Platinum)

---

## Cross-Cutting (Used Across All Tiers)

| Skill | Trigger | Description |
|-------|---------|-------------|
| `audit-logging` | Every action | Logs all AI actions to `Logs/YYYY-MM-DD.json` in the required JSON schema |
| `hitl-approval-requesting` | Sensitive action detected | Creates approval request `.md` files in `Pending_Approval/` with proper frontmatter |
| `dashboard-updating` | After any vault state change | Refreshes `Dashboard.md` with current system status, pending items, recent activity |
| `vault-triaging` | New items in `Needs_Action/` | Reads, classifies, and routes items from `Needs_Action/` into `Plans/` |

## Bronze — Foundation

| Skill | Trigger | Description |
|-------|---------|-------------|
| `email-triaging` | `EMAIL_*.md` appears in `Needs_Action/` | Classifies email priority, extracts intent, suggests actions per `Company_Handbook.md` rules |
| `file-processing` | `FILE_*.md` appears in `Needs_Action/` | Processes dropped files — extracts metadata, categorizes, routes to appropriate folder |
| `plan-generating` | Action item needs multi-step work | Creates `PLAN_*.md` files with checkboxes, dependencies, and approval flags |

## Silver — Functional Assistant

| Skill | Trigger | Description |
|-------|---------|-------------|
| `whatsapp-triaging` | `WHATSAPP_*.md` appears in `Needs_Action/` | Classifies WhatsApp messages, detects intent (invoice request, urgent help, etc.), suggests response |
| `email-drafting` | Plan step requires email reply | Drafts email replies following `Company_Handbook.md` tone rules, routes to `Pending_Approval/` |
| `linkedin-posting` | Scheduled or manual trigger | Generates business LinkedIn posts for lead generation, routes to `Pending_Approval/` before posting |
| `approval-executing` | File appears in `Approved/` | Reads approved action files, triggers the corresponding MCP action, moves to `Done/`, logs result |

## Gold — Autonomous Employee

| Skill | Trigger | Description |
|-------|---------|-------------|
| `ceo-briefing` | Weekly scheduled trigger (Sunday night) | Audits `Done/`, `Accounting/`, `Business_Goals.md` and generates `Monday_Briefing.md` in `Briefings/` |
| `transaction-auditing` | New entries in `Accounting/` | Analyzes bank transactions, flags unused subscriptions, detects anomalies per `Business_Goals.md` thresholds |
| `invoice-generating` | Client requests invoice (from any watcher) | Generates invoice from `Accounting/Rates.md` + client data, saves to `Invoices/`, creates email approval |
| `social-media-posting` | Scheduled or manual trigger | Generates posts for Facebook, Instagram, Twitter/X — formats per platform, routes to `Pending_Approval/` |
| `error-recovering` | Watcher/MCP failure detected | Applies retry logic with exponential backoff, quarantines corrupted items, alerts human on auth failures |

## Platinum — Cloud + Local

| Skill | Trigger | Description |
|-------|---------|-------------|
| `cloud-drafting` | Cloud agent processes `Needs_Action/` while local is offline | Drafts replies/posts, writes to `Pending_Approval/` for local approval — never executes directly |
| `vault-syncing` | Periodic or on-change | Manages git-based vault sync between cloud and local, enforces security rules (no secrets in sync) |
| `health-monitoring` | Periodic (every 60s) | Checks watcher/orchestrator PIDs, restarts failed processes, writes status to `Dashboard.md` |
| `claim-managing` | Multiple agents active | Handles claim-by-move concurrency — moves items to `In_Progress/<agent>/`, prevents double-work |
