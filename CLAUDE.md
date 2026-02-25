# CLAUDE.md — AI Employee Vault

## Project

Personal AI Employee — an autonomous, local-first Digital FTE built with Claude Code + Obsidian.
Hackathon project progressing through Bronze → Silver → Gold → Platinum tiers.
See `Docs/` for full architecture specs, tier checklists, and reference material.

## Owner

- **Name:** 404MW
- **Email:** 404mwaqas@gmail.com

## Agent Behavior

- **Mode: Conservative.** Always ask before acting. Never auto-approve. Prioritize safety over speed.
- Never execute external actions (send emails, make API calls, post to social media) without explicit user approval.
- Never delete files outside the vault without asking.
- Never commit, push, or modify git history without explicit instruction.
- When unsure about intent, ask a clarifying question rather than guessing.
- Reason first, document the plan, then implement only after confirmation.

## Environment

- **OS:** Windows (PowerShell)
- **Shell:** PowerShell (use PowerShell-compatible commands; no bash-only syntax)
- **Python:** 3.13+ via UV
- **Node.js:** v24+ LTS
- **Package manager:** UV for Python, npm for Node.js
- **Task scheduling:** Windows Task Scheduler (not cron)
- **Path separator:** Use `\` for Windows paths in scripts; `/` is acceptable in Python's `pathlib`

## Code Style — Python

- **Version:** 3.13+
- **Project manager:** UV (`uv init`, `uv add`, `uv run`)
- **Formatter:** Ruff (`ruff format`)
- **Linter:** Ruff (`ruff check`)
- **Type hints:** Required on all function signatures. Use `typing` module for complex types.
- **Docstrings:** Google style. Required on all public functions and classes.
- **Naming:**
  - `snake_case` for functions, variables, modules, file names
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
  - Prefix private members with `_`
- **Imports:** stdlib → third-party → local, separated by blank lines. Use absolute imports.
- **Error handling:** Explicit exception types. Never bare `except:`. Log errors before re-raising.
- **Logging:** Use `logging` module, never `print()` in production code.
- **Tests:** pytest. Test files named `test_*.py`. Fixtures in `conftest.py`.
- **Line length:** 88 characters (Ruff default).
- **String quotes:** Double quotes for strings.

## Code Style — Node.js / TypeScript

- **Runtime:** Node.js v24+ LTS
- **Package manager:** npm
- **Language:** TypeScript preferred over plain JS for MCP servers
- **Naming:**
  - `camelCase` for functions and variables
  - `PascalCase` for classes and interfaces
  - `UPPER_SNAKE_CASE` for constants
- **Formatting:** Prettier (default config)
- **Linting:** ESLint

## Vault Folder Structure

```
AI_Employee_Vault/
├── CLAUDE.md                  # This file — project instructions for Claude
├── Hackathon_Blueprint_Reference.md  # Original monolithic hackathon doc (reference only)
├── Docs/                      # Architecture specs, tier checklists, guides (read-only reference)
├── Dashboard.md               # Real-time system status (single-writer: local agent only)
├── Company_Handbook.md        # Rules of engagement for AI behavior
├── Business_Goals.md          # Objectives, metrics, audit rules
│
├── Inbox/                     # Raw incoming items before triage
├── Needs_Action/              # Triaged items awaiting Claude processing
├── Plans/                     # Claude-generated plan files with checkboxes
├── In_Progress/               # Items currently being worked on
│   └── <agent_name>/          # Claim-by-move: agent-specific work folders
├── Pending_Approval/          # HITL: items awaiting human approval
├── Approved/                  # Human-approved items ready for execution
├── Rejected/                  # Human-rejected items
├── Done/                      # Completed items (archive)
│
├── Accounting/                # Financial data, transactions, rates
├── Briefings/                 # Generated CEO briefings
├── Logs/                      # JSON audit logs (YYYY-MM-DD.json)
├── Invoices/                  # Generated invoice files
│
├── Scripts/                   # Python watcher scripts, orchestrator, utilities
├── .env                       # Secrets — NEVER commit (in .gitignore)
└── .gitignore
```

## File Naming Conventions

| Source | Pattern | Example |
|--------|---------|---------|
| Gmail Watcher | `EMAIL_<message_id>.md` | `EMAIL_18d3f2a1b4c.md` |
| WhatsApp Watcher | `WHATSAPP_<contact>_<YYYY-MM-DD>.md` | `WHATSAPP_client_a_2026-02-25.md` |
| File System Watcher | `FILE_<original_name>.md` | `FILE_report.pdf.md` |
| Plans | `PLAN_<task_slug>.md` | `PLAN_invoice_client_a.md` |
| Approval Requests | `<ACTION>_<target>_<YYYY-MM-DD>.md` | `PAYMENT_Client_A_2026-02-25.md` |
| CEO Briefings | `<YYYY-MM-DD>_Monday_Briefing.md` | `2026-02-24_Monday_Briefing.md` |
| Audit Logs | `<YYYY-MM-DD>.json` | `2026-02-25.json` |

## Frontmatter Schema

All action files in the vault use YAML frontmatter:

```yaml
---
type: email | whatsapp | file_drop | approval_request | plan | briefing
status: pending | in_progress | approved | rejected | done
priority: low | normal | high | urgent
created: <ISO 8601 timestamp>
source: gmail_watcher | whatsapp_watcher | filesystem_watcher | manual
---
```

## Key Architecture References

- **System architecture:** `Docs/06_Architecture.md`
- **Watcher patterns:** `Docs/07_Watcher_Architecture.md`
- **MCP setup:** `Docs/08_MCP_Configuration.md`
- **Ralph Wiggum loop:** `Docs/09_Ralph_Wiggum_Loop.md`
- **Security rules:** `Docs/11_Security_Privacy.md`
- **Current tier progress:** `Docs/02_Tier_Bronze.md` (start here)

## Agent Skills

All AI functionality must be implemented as [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).
This is a **hard requirement across every tier** (Bronze through Platinum).

- Package each discrete AI capability as a reusable Agent Skill (e.g., email triage, invoice generation, CEO briefing)
- Skills live in `.claude/skills/` following the Claude Agent Skills spec
- Each skill should be self-contained with a clear trigger, input, and output
- Prefer skills over ad-hoc prompts — if Claude does it more than once, it should be a skill
- Reference: `Docs/16_Learning_Resources.md` for Agent Skills tutorials

## Rules

1. Never store secrets in markdown files or commit them to git.
2. All external actions must go through the HITL approval flow (`Pending_Approval/` → `Approved/`).
3. Every action must be audit-logged to `Logs/`.
4. Use `DRY_RUN=true` by default in all scripts. Never flip to `false` without user instruction.
5. When creating watcher scripts, always extend `BaseWatcher` from `Scripts/base_watcher.py`.
6. Dashboard.md is single-writer (local agent only). Cloud agents write to `Updates/` for merge.
7. Claim-by-move: first agent to move an item from `Needs_Action/` to `In_Progress/<agent>/` owns it.
8. All AI functionality must be packaged as Agent Skills — no loose one-off prompts in production.
