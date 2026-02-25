# Tier: Bronze — Foundation (Minimum Viable Deliverable)

**Estimated time:** 8-12 hours

## Checklist

- [x] Obsidian vault with `Dashboard.md` and `Company_Handbook.md`
- [x] One working Watcher script (Gmail OR file system monitoring)
- [x] Claude Code successfully reading from and writing to the vault
- [x] Basic folder structure: `/Inbox`, `/Needs_Action`, `/Done`
- [x] All AI functionality implemented as [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

## Key Deliverables

1. **Dashboard.md** — Real-time summary of pending messages and active tasks
2. **Company_Handbook.md** — Rules of Engagement for the AI (e.g., tone, approval thresholds)
3. **One Watcher** — A Python script that monitors a source (Gmail or filesystem) and writes `.md` files into `/Needs_Action`
4. **Claude Code integration** — Claude reads from `/Needs_Action`, processes items, moves to `/Done`
5. **Agent Skills** — Package AI functionality as reusable skills

## Reference Docs

- Architecture: [[06_Architecture]]
- Watcher patterns: [[07_Watcher_Architecture]]
- Security basics: [[11_Security_Privacy]]
