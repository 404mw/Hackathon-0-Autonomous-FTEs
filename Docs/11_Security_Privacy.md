# Security & Privacy Architecture

Security is non-negotiable when building an autonomous system that handles banking, email, and personal communications.

## 6.1 Credential Management

Never store credentials in plain text or in your Obsidian vault.

- Use environment variables for API keys: `export GMAIL_API_KEY="your-key"`
- For banking credentials, use a dedicated secrets manager (e.g., macOS Keychain, Windows Credential Manager, or 1Password CLI)
- Create a `.env` file (add to `.gitignore` immediately) for local development
- Rotate credentials monthly and after any suspected breach

Example `.env` structure:

```env
# .env - NEVER commit this file
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
BANK_API_TOKEN=your_token
WHATSAPP_SESSION_PATH=/secure/path/session
```

## 6.2 Sandboxing & Isolation

Protect against unintended actions during development:

- **Development Mode:** Create a `DEV_MODE` flag that prevents any real external actions
- **Dry Run:** All action scripts should support a `--dry-run` flag that logs intended actions without executing
- **Separate Accounts:** Use test/sandbox accounts for Gmail and banking during development
- **Rate Limiting:** Implement maximum actions per hour (e.g., max 10 emails, max 3 payments)

Example dry-run implementation:

```python
# In any action script
DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'

def send_email(to, subject, body):
    if DRY_RUN:
        logger.info(f'[DRY RUN] Would send email to {to}')
        return
    # Actual send logic here
```

## 6.3 Audit Logging

Every action the AI takes must be logged for review:

```json
{
  "timestamp": "2026-01-07T10:30:00Z",
  "action_type": "email_send",
  "actor": "claude_code",
  "target": "client@example.com",
  "parameters": {"subject": "Invoice #123"},
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```

Store logs in `/Vault/Logs/YYYY-MM-DD.json` and retain for a minimum 90 days.

## 6.4 Permission Boundaries

| Action Category | Auto-Approve Threshold | Always Require Approval |
| :--- | :--- | :--- |
| Email replies | To known contacts | New contacts, bulk sends |
| Payments | < $50 recurring | All new payees, > $100 |
| Social media | Scheduled posts | Replies, DMs |
| File operations | Create, read | Delete, move outside vault |
