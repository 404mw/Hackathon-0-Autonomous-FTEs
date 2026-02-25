# Example: End-to-End Invoice Flow

This walkthrough demonstrates a complete flow from trigger to action, showing how all components work together.

## Scenario

A client sends a WhatsApp message asking for an invoice. The AI Employee should:
1. Detect the request
2. Generate the invoice
3. Send it via email
4. Log the transaction

---

## Step 1: Detection (WhatsApp Watcher)

The WhatsApp Watcher detects a message containing the keyword "invoice":

```
# Detected message:
# From: Client A
# Text: "Hey, can you send me the invoice for January?"

# Watcher creates:
# /Vault/Needs_Action/WHATSAPP_client_a_2026-01-07.md
```

## Step 2: Reasoning (Claude Code)

The Orchestrator triggers Claude to process the Needs_Action folder:

```markdown
# Claude reads the file and creates:
# /Vault/Plans/PLAN_invoice_client_a.md

---
created: 2026-01-07T10:30:00Z
status: pending_approval
---

## Objective
Generate and send January invoice to Client A

## Steps
- [x] Identify client: Client A (client_a@email.com)
- [x] Calculate amount: $1,500 (from /Accounting/Rates.md)
- [ ] Generate invoice PDF
- [ ] Send via email (REQUIRES APPROVAL)
- [ ] Log transaction

## Approval Required
Email send requires human approval. See /Pending_Approval/
```

## Step 3: Approval (Human-in-the-Loop)

Claude creates an approval request:

```markdown
# /Vault/Pending_Approval/EMAIL_invoice_client_a.md
---
action: send_email
to: client_a@email.com
subject: January 2026 Invoice - $1,500
attachment: /Vault/Invoices/2026-01_Client_A.pdf
---

Ready to send. Move to /Approved to proceed.
```

You review and move the file to `/Approved`.

## Step 4: Action (Email MCP)

The Orchestrator detects the approved file and calls the Email MCP:

```javascript
// MCP call (simplified)
await email_mcp.send_email({
  to: 'client_a@email.com',
  subject: 'January 2026 Invoice - $1,500',
  body: 'Please find attached your invoice for January 2026.',
  attachment: '/Vault/Invoices/2026-01_Client_A.pdf'
});

// Result logged to /Vault/Logs/2026-01-07.json
```

## Step 5: Completion

Claude updates the Dashboard and moves files to Done:

```
# /Vault/Dashboard.md updated:
## Recent Activity
- [2026-01-07 10:45] Invoice sent to Client A ($1,500)

# Files moved:
# /Needs_Action/WHATSAPP_... -> /Done/
# /Plans/PLAN_invoice_... -> /Done/
# /Approved/EMAIL_... -> /Done/
```
