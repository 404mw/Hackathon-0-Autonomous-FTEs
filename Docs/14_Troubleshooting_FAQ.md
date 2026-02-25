# Troubleshooting FAQ

## Setup Issues

**Q: Claude Code says "command not found"**
A: Ensure Claude Code is installed globally and your PATH is configured. Run: `npm install -g @anthropic/claude-code`, then restart your terminal.

**Q: Obsidian vault isn't being read by Claude**
A: Check that you're running Claude Code from the vault directory, or using the `--cwd` flag to point to it. Verify file permissions allow read access.

**Q: Gmail API returns 403 Forbidden**
A: Your OAuth consent screen may need verification, or you haven't enabled the Gmail API in Google Cloud Console. Check the project settings.

---

## Runtime Issues

**Q: Watcher scripts stop running overnight**
A: Use a process manager like PM2 (Node.js) or supervisord (Python) to keep them alive. Alternatively, implement the Watchdog pattern from [[12_Error_Recovery]].

**Q: Claude is making incorrect decisions**
A: Review your `Company_Handbook.md` rules. Add more specific examples. Consider lowering autonomy thresholds so more actions require approval.

**Q: MCP server won't connect**
A: Check that the server process is running (`ps aux | grep mcp`). Verify the path in `mcp.json` is absolute. Check Claude Code logs for connection errors.

---

## Security Concerns

**Q: How do I know my credentials are safe?**
A: Never commit `.env` files. Use environment variables. Regularly rotate credentials. Implement the audit logging from [[11_Security_Privacy]] to track all access.

**Q: What if Claude tries to pay the wrong person?**
A: That's why HITL is critical for payments. Any payment action should create an approval file first. Never auto-approve payments to new recipients.
