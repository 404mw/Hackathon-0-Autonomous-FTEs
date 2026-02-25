# Tier: Silver — Functional Assistant

**Estimated time:** 20-30 hours

## Prerequisites

- [ ] **All Bronze tier requirements completed** (see [[02_Tier_Bronze]])

## Additional Checklist

- [ ] Two or more Watcher scripts (e.g., Gmail + WhatsApp + LinkedIn)
- [ ] Automatically post on LinkedIn about business to generate sales
- [ ] Claude reasoning loop that creates `Plan.md` files
- [ ] One working MCP server for external action (e.g., sending emails)
- [ ] Human-in-the-loop approval workflow for sensitive actions
- [ ] Basic scheduling via cron or Task Scheduler
- [ ] All AI functionality implemented as [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

## Key Additions Over Bronze

1. **Multiple Watchers** — Expand perception to 2+ sources
2. **Social Media Automation** — LinkedIn posting for lead generation
3. **Planning Loop** — Claude creates `Plan.md` files with checkboxes before acting
4. **MCP Server** — At least one external action capability (email send, etc.)
5. **HITL Workflow** — `/Pending_Approval` → `/Approved` file-based approval system
6. **Scheduling** — Automated triggers via cron (Linux/Mac) or Task Scheduler (Windows)

## Reference Docs

- MCP setup: [[08_MCP_Configuration]]
- HITL pattern: [[08_MCP_Configuration#Human-in-the-Loop Pattern]]
- Business handover: [[10_Business_Handover]]
