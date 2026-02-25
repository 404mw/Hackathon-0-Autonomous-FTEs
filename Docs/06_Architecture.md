# Architecture: Perception → Reasoning → Action

## The Foundational Layer (Local Engine)

### The Nerve Center (Obsidian)
Acts as the **GUI** and **Long-Term Memory**.
- **Dashboard.md:** Real-time summary of bank balance, pending messages, and active business projects
- **Company_Handbook.md:** Contains your "Rules of Engagement" (e.g., "Always be polite on WhatsApp," "Flag any payment over $500 for my approval")

### The Muscle (Claude Code)
Runs in your terminal, pointed at your Obsidian vault. It uses its File System tools to read tasks and write reports. The Ralph Wiggum loop (a Stop hook) keeps Claude iterating until multi-step tasks are complete.

---

## Perception → Reasoning → Action Flow

### A. Perception (The "Watchers")
Since Claude Code can't "listen" to the internet 24/7, lightweight **Python Sentinel Scripts** run in the background:
- **Comms Watcher:** Monitors Gmail and WhatsApp, saves urgent messages as `.md` files in `/Needs_Action`
- **Finance Watcher:** Downloads CSVs or calls banking APIs to log transactions in `/Accounting/Current_Month.md`
- Watchers can "wake up" as soon as you open your machine

### B. Reasoning (Claude Code)
When the Watcher detects a change, it triggers Claude:
1. **Read:** "Check `/Needs_Action` and `/Accounting`."
2. **Think:** "I see a WhatsApp message from a client asking for an invoice and a bank transaction showing a late payment fee."
3. **Plan:** Claude creates a `Plan.md` in Obsidian with checkboxes for next steps.

### C. Action (The "Hands")
MCP servers are Claude Code's hands for interacting with external systems:
- **WhatsApp/Social MCP:** Send replies or post scheduled updates
- **Browser/Payment MCP:** Log into payment portals, draft payments, and stop
- **Human-in-the-Loop (HITL):** Claude writes `APPROVAL_REQUIRED_*.md` — it will not execute until you move it to `/Approved`

### D. Persistence (The "Ralph Wiggum" Loop)
See [[09_Ralph_Wiggum_Loop]] for details on the stop-hook pattern that keeps Claude working autonomously until tasks complete.

---

## Continuous vs. Scheduled Operations

| Operation Type | Example Task | Local Trigger |
| :--- | :--- | :--- |
| **Scheduled** | Daily Briefing: Summarize business tasks at 8:00 AM | cron (Mac/Linux) or Task Scheduler (Win) |
| **Continuous** | Lead Capture: Watch WhatsApp for keywords like "Pricing" | Python watchdog script monitoring `/Inbox` |
| **Project-Based** | Q1 Tax Prep: Categorize 3 months of expenses | Manual drag-and-drop into `/Active_Project` |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERSONAL AI EMPLOYEE                         │
│                      SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SOURCES                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│     Gmail       │    WhatsApp     │     Bank APIs    │  Files   │
└────────┬────────┴────────┬────────┴─────────┬────────┴────┬─────┘
         │                 │                  │             │
         ▼                 ▼                  ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Gmail Watcher│ │WhatsApp Watch│ │Finance Watcher│           │
│  │  (Python)    │ │ (Playwright) │ │   (Python)   │            │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT (Local)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ /Needs_Action/  │ /Plans/  │ /Done/  │ /Logs/            │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Dashboard.md    │ Company_Handbook.md │ Business_Goals.md│  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ /Pending_Approval/  │  /Approved/  │  /Rejected/         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REASONING LAYER                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                      CLAUDE CODE                          │ │
│  │   Read → Think → Plan → Write → Request Approval          │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┴───────────────────┐
              ▼                                      ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│    HUMAN-IN-THE-LOOP       │    │         ACTION LAYER           │
│  ┌──────────────────────┐  │    │  ┌─────────────────────────┐   │
│  │ Review Approval Files│──┼───▶│  │    MCP SERVERS          │   │
│  │ Move to /Approved    │  │    │  │  ┌──────┐ ┌──────────┐  │   │
│  └──────────────────────┘  │    │  │  │Email │ │ Browser  │  │   │
│                            │    │  │  │ MCP  │ │   MCP    │  │   │
└────────────────────────────┘    │  │  └──┬───┘ └────┬─────┘  │   │
                                  │  └─────┼──────────┼────────┘   │
                                  └────────┼──────────┼────────────┘
                                           │          │
                                           ▼          ▼
                                  ┌────────────────────────────────┐
                                  │     EXTERNAL ACTIONS           │
                                  │  Send Email │ Make Payment     │
                                  │  Post Social│ Update Calendar  │
                                  └────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Orchestrator.py (Master Process)             │ │
│  │   Scheduling │ Folder Watching │ Process Management       │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Watchdog.py (Health Monitor)                 │ │
│  │   Restart Failed Processes │ Alert on Errors              │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```
