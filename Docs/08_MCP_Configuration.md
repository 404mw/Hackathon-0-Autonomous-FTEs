# MCP Configuration & Human-in-the-Loop

Model Context Protocol (MCP) servers are Claude Code's hands for interacting with external systems. Each MCP server exposes specific capabilities that Claude can invoke.

## Recommended MCP Servers

| Server | Capabilities | Use Case |
| :--- | :--- | :--- |
| filesystem | Read, write, list files | Built-in, use for vault |
| email-mcp | Send, draft, search emails | Gmail integration |
| browser-mcp | Navigate, click, fill forms | Payment portals |
| calendar-mcp | Create, update events | Scheduling |
| slack-mcp | Send messages, read channels | Team communication |

## Claude Code Configuration

Configure MCP servers in your Claude Code settings:

```json
// ~/.config/claude-code/mcp.json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json"
      }
    },
    {
      "name": "browser",
      "command": "npx",
      "args": ["@anthropic/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  ]
}
```

---

## Human-in-the-Loop Pattern

For sensitive actions, Claude writes an approval request file instead of acting directly:

```markdown
# /Vault/Pending_Approval/PAYMENT_Client_A_2026-01-07.md
---
type: approval_request
action: payment
amount: 500.00
recipient: Client A
reason: Invoice #1234 payment
created: 2026-01-07T10:30:00Z
expires: 2026-01-08T10:30:00Z
status: pending
---

## Payment Details
- Amount: $500.00
- To: Client A (Bank: XXXX1234)
- Reference: Invoice #1234

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

The Orchestrator watches the `/Approved` folder and triggers the actual MCP action when files appear.

## Permission Boundaries

| Action Category | Auto-Approve Threshold | Always Require Approval |
| :--- | :--- | :--- |
| Email replies | To known contacts | New contacts, bulk sends |
| Payments | < $50 recurring | All new payees, > $100 |
| Social media | Scheduled posts | Replies, DMs |
| File operations | Create, read | Delete, move outside vault |
