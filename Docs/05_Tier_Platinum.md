# Tier: Platinum — Always-On Cloud + Local Executive

**Estimated time:** 60+ hours

## Prerequisites

- [ ] **All Gold tier requirements completed** (see [[04_Tier_Gold]])

## Additional Checklist

- [ ] Run the AI Employee on Cloud 24/7 (always-on watchers + orchestrator + health monitoring). Deploy a Cloud VM (e.g., [Oracle Cloud Free VMs](https://www.oracle.com/cloud/free/))
- [ ] Work-Zone Specialization (domain ownership):
  - [ ] **Cloud owns:** Email triage + draft replies + social post drafts/scheduling (draft-only; requires Local approval before send/post)
  - [ ] **Local owns:** Approvals, WhatsApp session, payments/banking, and final "send/post" actions
- [ ] Delegation via Synced Vault (Phase 1):
  - [ ] Agents communicate by writing files into: `/Needs_Action/<domain>/`, `/Plans/<domain>/`, `/Pending_Approval/<domain>/`
  - [ ] Prevent double-work using:
    - [ ] `/In_Progress/<agent>/` claim-by-move rule
    - [ ] Single-writer rule for `Dashboard.md` (Local)
    - [ ] Cloud writes updates to `/Updates/` (or `/Signals/`), Local merges into `Dashboard.md`
  - [ ] Vault sync via Git (recommended) or Syncthing
  - [ ] **Claim-by-move rule:** First agent to move item from `/Needs_Action` to `/In_Progress/<agent>/` owns it; others ignore
- [ ] **Security rule:** Vault sync includes only markdown/state. Secrets never sync (.env, tokens, WhatsApp sessions, banking creds). Cloud never stores or uses WhatsApp sessions, banking credentials, or payment tokens
- [ ] Deploy Odoo Community on Cloud VM (24/7) with HTTPS, backups, and health monitoring. Integrate Cloud Agent with Odoo via MCP for draft-only accounting actions and Local approval for posting invoices/payments
- [ ] Optional A2A Upgrade (Phase 2): Replace some file handoffs with direct A2A messages, keeping vault as audit record

## Platinum Demo (Minimum Passing Gate)

Email arrives while Local is offline → Cloud drafts reply + writes approval file → when Local returns, user approves → Local executes send via MCP → logs → moves task to `/Done`.

## Key Additions Over Gold

1. **Cloud Deployment** — Always-on VM running watchers + orchestrator 24/7
2. **Dual-Agent Architecture** — Cloud agent (drafts) + Local agent (approvals/execution)
3. **Vault Sync** — Git-based sync with security boundaries (no secrets in sync)
4. **Claim-by-Move** — Concurrency control via file-based locking
5. **Cloud Odoo** — Production Odoo deployment with HTTPS and backups
6. **A2A Ready** — Optional upgrade path from file-based to direct agent-to-agent messaging

## Reference Docs

- Architecture: [[06_Architecture]]
- Security: [[11_Security_Privacy]]
- Error recovery: [[12_Error_Recovery]]
- Advanced Cloud FTE: https://docs.google.com/document/d/15GuwZwIOQy_g1XsIJjQsFNHCTQTWoXQhWGVMhiH0swc/edit?usp=sharing
