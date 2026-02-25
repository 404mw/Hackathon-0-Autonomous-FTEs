# Personal AI Employee Hackathon 0: Building Autonomous FTEs in 2026

**Tagline:** *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

This document serves as a comprehensive architectural blueprint and hackathon guide for building a "Digital FTE" (Full-Time Equivalent). It proposes a futuristic, local-first approach to automation where an AI agent—powered by Claude Code and Obsidian—proactively manages personal and business affairs 24/7. You can also think of it as a "Smart Consultant" (General Agents). The focus is on high-level reasoning, autonomy, and flexibility. Think of it as hiring a senior employee who figures out how to solve the problems.

This hackathon takes the concept of a "Personal AI Employee" to its logical extreme. It doesn't just wait for you to type; it proactively manages your "Personal Affairs" (Gmail, WhatsApp, Bank) and your "Business" (Social Media, Payments, Project Tasks) using **Claude Code** as the executor and **Obsidian** as the management dashboard.

All our faculty members and students will build this Personal AI Employee using Claude Code.

**Standout Idea:** The "Monday Morning CEO Briefing," where the AI autonomously audits bank transactions and tasks to report revenue and bottlenecks, transforms the AI from a chatbot into a proactive business partner.

---

## Digital FTE: The New Unit of Value

A Digital FTE (Full-Time Equivalent) is an AI agent that is built, "hired," and priced as if it were a human employee. This shifts the conversation from "software licenses" to "headcount budgets."

### Human FTE vs Digital FTE

| Feature | Human FTE | Digital FTE (Custom Agent) |
| --- | --- | --- |
| Availability | 40 hours / week | 168 hours / week (24/7) |
| Monthly Cost | $4,000 – $8,000+ | $500 – $2,000 |
| Ramp-up Time | 3 – 6 Months | Instant (via SKILL.md) |
| Consistency | Variable (85–95% accuracy) | Predictable (99%+ consistency) |
| Scaling | Linear (Hire 10 for 10x work) | Exponential (Instant duplication) |
| Cost per Task | ~$3.00 – $6.00 | ~$0.25 – $0.50 |
| Annual Hours | ~2,000 hours | ~8,760 hours |

**The 'Aha!' Moment:** A Digital FTE works nearly 9,000 hours a year vs a human's 2,000. The cost per task reduction (from ~$5.00 to ~$0.50) is an 85–90% cost saving—usually the threshold where a CEO approves a project without further debate.

---

## Tech Stack Summary

- **Knowledge Base:** Obsidian (Local Markdown)
- **Logic Engine:** Claude Code (running claude-4-5-opus or any other LLM using Claude Code Router)
- **External Integration:** MCP Servers (Local Node.js/Python scripts) for Gmail, WhatsApp, and Banking
  - Playwright for "Computer Use" (interacting with websites for payments)
- **Automation Glue:** A master Python `Orchestrator.py` that handles timing and folder watching

## Core Strengths

- **Local-First:** Privacy-centric architecture using Obsidian
- **HITL Safety:** Sophisticated file-based approval system prevents AI accidents
