"""Email Send MCP Server for the AI Employee vault.

Exposes three Gmail tools to Claude Code via the Model Context Protocol:
  - send_email    — sends an email via the Gmail API
  - draft_email   — saves a Gmail draft without sending
  - list_drafts   — returns recent draft subjects for review

All tools honour the DRY_RUN environment variable (default: true).
send_email and draft_email require a token.json that includes the
gmail.send scope — run Scripts/gmail_auth.py to generate one.

Registration (run once):
    claude mcp add email-send \\
        --command uv \\
        --args "run python Scripts/mcp_servers/email_send/server.py" \\
        --cwd "G:/Hackathons/GIAIC_Hackathons/AI_Employee_Vault"

Usage (after registration):
    Claude Code will call the tools automatically.
    To run the server manually:
        uv run python Scripts/mcp_servers/email_send/server.py

Environment variables (or set in .env):
    GMAIL_TOKEN_PATH        Path to token.json (must include gmail.send scope)
    GMAIL_CREDENTIALS_PATH  Path to credentials.json
    DRY_RUN                 If "true", log actions but do not call Gmail API (default: true)
"""

import base64
import logging
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Both scopes needed: readonly for list_drafts context; send for send/draft
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Vault root: Scripts/mcp_servers/email_send/server.py → 3 levels up
_VAULT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

mcp = FastMCP("email-send")


# ------------------------------------------------------------------
# Gmail service helper
# ------------------------------------------------------------------


def _resolve_path(env_var: str, default_relative: str) -> Path:
    """Resolve a path from an env var, falling back to a vault-relative default.

    Args:
        env_var: Environment variable name to check first.
        default_relative: Relative path from vault root if env var is not set.

    Returns:
        Resolved absolute Path.
    """
    raw = os.environ.get(env_var, "")
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else _VAULT_ROOT / p
    return _VAULT_ROOT / default_relative


def _get_gmail_service():
    """Load OAuth credentials and return an authenticated Gmail API service.

    Returns:
        A Gmail API Resource object authenticated with gmail.send scope.

    Raises:
        RuntimeError: If token.json is missing or credentials cannot be refreshed.
    """
    token_path = _resolve_path("GMAIL_TOKEN_PATH", "Scripts/token.json")

    if not token_path.exists():
        raise RuntimeError(
            f"Token file not found: {token_path}\n"
            "Run 'uv run python Scripts/gmail_auth.py' with the gmail.send scope "
            "to generate a new token."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token")
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                "Gmail credentials are invalid and cannot be refreshed.\n"
                "Run 'uv run python Scripts/gmail_auth.py' to re-authenticate."
            )

    return build("gmail", "v1", credentials=creds)


def _build_raw_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
) -> str:
    """Build a base64url-encoded RFC 822 message string.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        cc: Optional CC address or comma-separated addresses.

    Returns:
        Base64url-encoded message string suitable for the Gmail API ``raw`` field.
    """
    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = to
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")


# ------------------------------------------------------------------
# MCP tools
# ------------------------------------------------------------------


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    reply_to_thread_id: str | None = None,
) -> dict:
    """Send an email via the Gmail API.

    Requires human approval before being called — use only from the
    approval-executing skill after a user has moved an approval request
    to Approved/.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        cc: Optional CC address (or comma-separated list).
        reply_to_thread_id: Gmail thread ID to reply into; omit for a new thread.

    Returns:
        Dict with message_id, thread_id, and timestamp on success.
        In DRY_RUN mode, returns {dry_run: True, would_send_to: <to>}.
    """
    if os.environ.get("DRY_RUN", "true").lower() == "true":
        logger.info(
            "[DRY_RUN] Would send email to=%r subject=%r body_len=%d",
            to,
            subject,
            len(body),
        )
        return {"dry_run": True, "would_send_to": to, "subject": subject}

    raw = _build_raw_message(to, subject, body, cc=cc)
    message_body: dict = {"raw": raw}
    if reply_to_thread_id:
        message_body["threadId"] = reply_to_thread_id

    service = _get_gmail_service()
    result = service.users().messages().send(userId="me", body=message_body).execute()

    logger.info("Email sent: message_id=%s thread_id=%s", result["id"], result.get("threadId"))
    return {
        "message_id": result["id"],
        "thread_id": result.get("threadId", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def draft_email(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
) -> dict:
    """Save an email as a Gmail draft without sending.

    Use this when the email-drafting skill produces a draft for human review
    before the send step. In DRY_RUN mode, logs the draft but does not call
    the Gmail API.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        cc: Optional CC address (or comma-separated list).

    Returns:
        Dict with draft_id and timestamp on success.
        In DRY_RUN mode, returns {dry_run: True, would_draft_to: <to>}.
    """
    if os.environ.get("DRY_RUN", "true").lower() == "true":
        logger.info(
            "[DRY_RUN] Would create draft to=%r subject=%r body_len=%d",
            to,
            subject,
            len(body),
        )
        return {"dry_run": True, "would_draft_to": to, "subject": subject}

    raw = _build_raw_message(to, subject, body, cc=cc)
    service = _get_gmail_service()
    result = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    logger.info("Draft created: draft_id=%s", result["id"])
    return {
        "draft_id": result["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def list_drafts() -> list[dict]:
    """Return the 10 most recent Gmail drafts with subject and recipient.

    Useful for the email-drafting skill to check what drafts are pending
    review before requesting approval.

    Returns:
        List of dicts, each with draft_id, subject, and to fields.
        Returns an empty list in DRY_RUN mode.
    """
    if os.environ.get("DRY_RUN", "true").lower() == "true":
        logger.info("[DRY_RUN] Would list Gmail drafts")
        return []

    service = _get_gmail_service()
    result = service.users().drafts().list(userId="me", maxResults=10).execute()
    raw_drafts: list[dict] = result.get("drafts", [])

    drafts: list[dict] = []
    for draft in raw_drafts:
        detail = service.users().drafts().get(
            userId="me",
            id=draft["id"],
            format="metadata",
            metadataHeaders=["Subject", "To"],
        ).execute()
        headers: list[dict] = (
            detail.get("message", {}).get("payload", {}).get("headers", [])
        )
        subject = next(
            (h["value"] for h in headers if h["name"].lower() == "subject"),
            "(no subject)",
        )
        to_addr = next(
            (h["value"] for h in headers if h["name"].lower() == "to"),
            "",
        )
        drafts.append({"draft_id": draft["id"], "subject": subject, "to": to_addr})

    logger.info("Listed %d draft(s)", len(drafts))
    return drafts


if __name__ == "__main__":
    mcp.run()
