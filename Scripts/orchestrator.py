"""Orchestrator -- approval dispatcher for the AI Employee vault.

Watches the Approved/ directory on a configurable interval.
For each *.md approval file found:
  1. Parses YAML frontmatter to extract action type and parameters.
  2. Checks the expires field -- skips stale approvals.
  3. Routes to the correct handler:
       - send_email      → Gmail API (same OAuth token as gmail_watcher)
       - post_linkedin   → LinkedInPoster class (linkedin_poster.py)
       - whatsapp_reply  → logs manual instructions (no auto-send)
       - discord_reply   → logs manual instructions (no auto-send)
  4. Moves the file to Done/ with status updated.
  5. Appends an audit log entry to Logs/<YYYY-MM-DD>.json.

Respects DRY_RUN=true (default) -- logs intended actions without calling
any external service or writing any files.

Usage:
    uv run python Scripts/orchestrator.py

Environment variables (or set in .env):
    VAULT_PATH              Root path to vault (default: parent of Scripts/)
    ORCHESTRATOR_INTERVAL   Seconds between Approved/ scans (default: 10)
    GMAIL_TOKEN_PATH        Path to Gmail OAuth token (default: Scripts/token.json)
    GMAIL_CREDENTIALS_PATH  Path to Gmail credentials (default: Scripts/credentials.json)
    LINKEDIN_ACCESS_TOKEN   LinkedIn OAuth bearer token
    LINKEDIN_PERSON_URN     urn:li:person:<id> from linkedin_auth.py
    DRY_RUN                 If "true", log actions without executing (default: true)
"""

import base64
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))

VAULT_ROOT = Path(os.environ.get("VAULT_PATH", str(_SCRIPTS_DIR.parent)))
APPROVED_DIR = VAULT_ROOT / "Approved"
DONE_DIR = VAULT_ROOT / "Done"
LOGS_DIR = VAULT_ROOT / "Logs"

CHECK_INTERVAL = int(os.environ.get("ORCHESTRATOR_INTERVAL", "10"))
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"

_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR.mkdir(parents=True, exist_ok=True)

_log_file = LOGS_DIR / "orchestrator.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [Orchestrator] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file.

    Handles simple ``key: value`` and ``key: "quoted value"`` lines.
    Does not support nested YAML or multi-line values.

    Args:
        content: Full file content including the frontmatter block.

    Returns:
        Tuple of (frontmatter_dict, body_text_after_frontmatter).
    """
    if not content.startswith("---"):
        return {}, content

    end_idx = content.find("\n---", 3)
    if end_idx == -1:
        return {}, content

    fm_text = content[3:end_idx].strip()
    body = content[end_idx + 4 :].strip()

    fm: dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" not in line or line.startswith("#"):
            continue
        key, _, raw_value = line.partition(":")
        value = raw_value.strip().strip('"').strip("'")
        fm[key.strip()] = value

    return fm, body


def _extract_section(body: str, header: str) -> str:
    """Extract content from a named markdown section.

    Args:
        body: Markdown body text (without frontmatter).
        header: Section header text, without the leading ``## ``.

    Returns:
        Section content stripped of leading/trailing whitespace,
        or an empty string if the section is not found.
    """
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


# ---------------------------------------------------------------------------
# Expiry check
# ---------------------------------------------------------------------------


def _is_expired(fm: dict[str, str]) -> bool:
    """Return True if the approval file has passed its expiry time.

    Args:
        fm: Parsed frontmatter dict.

    Returns:
        True if the ``expires`` field is set and is in the past; False otherwise.
    """
    expires_str = fm.get("expires", "")
    if not expires_str:
        return False

    try:
        expires_dt = datetime.fromisoformat(expires_str)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc) > expires_dt
    except ValueError:
        logger.warning(
            "Could not parse expires field: %r -- treating as non-expired", expires_str
        )
        return False


# ---------------------------------------------------------------------------
# Gmail sending
# ---------------------------------------------------------------------------


def _get_gmail_service():
    """Build and return an authenticated Gmail API service.

    Returns:
        Gmail API Resource object authenticated with gmail.send scope.

    Raises:
        RuntimeError: If the token file is missing or cannot be refreshed.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    raw_token = os.environ.get("GMAIL_TOKEN_PATH", "")
    token_path = Path(raw_token) if raw_token else VAULT_ROOT / "Scripts" / "token.json"

    if not token_path.exists():
        raise RuntimeError(
            f"Gmail token not found: {token_path}\n"
            "Run 'uv run python Scripts/gmail_auth.py' to authenticate."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), _GMAIL_SCOPES)

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


def _send_email(fm: dict[str, str], body: str) -> str:
    """Send an email via the Gmail API.

    Reads the recipient, subject, and optional thread ID from frontmatter.
    Reads the email body from the ``## Draft Reply`` section.

    Args:
        fm: Parsed frontmatter dict with ``to``, ``subject``, and optional
            ``thread_id`` fields.
        body: Markdown body text containing a ``## Draft Reply`` section.

    Returns:
        Result string: ``"sent:<message_id>"`` on success, or ``"dry_run"``.

    Raises:
        ValueError: If required frontmatter fields or draft section are missing.
        RuntimeError: If Gmail service cannot be initialised.
    """
    to = fm.get("to", "")
    subject = fm.get("subject", "(no subject)")
    thread_id = fm.get("thread_id", "")

    if not to:
        raise ValueError("Approval file is missing the 'to' field in frontmatter")

    draft_text = _extract_section(body, "Draft Reply")
    if not draft_text:
        raise ValueError("Approval file is missing a '## Draft Reply' section")

    if DRY_RUN:
        logger.info("[DRY_RUN] Would send email to=%r subject=%r", to, subject)
        return "dry_run"

    msg = MIMEText(draft_text, "plain", "utf-8")
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    send_body: dict = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    service = _get_gmail_service()
    result = service.users().messages().send(userId="me", body=send_body).execute()
    message_id: str = result.get("id", "unknown")
    logger.info("Email sent -- message_id=%s to=%s", message_id, to)
    return f"sent:{message_id}"


# ---------------------------------------------------------------------------
# LinkedIn posting
# ---------------------------------------------------------------------------


def _post_linkedin(fm: dict[str, str], body: str) -> str:
    """Post an approved update to LinkedIn via LinkedInPoster.

    Reads the post text from the ``## Draft Content`` section.

    Args:
        fm: Parsed frontmatter dict (unused beyond logging context).
        body: Markdown body text containing a ``## Draft Content`` section.

    Returns:
        Result string: ``"posted:<id>"`` on success, or ``"dry_run"``.

    Raises:
        ValueError: If the ``## Draft Content`` section is missing.
        RuntimeError: If LinkedInPoster cannot authenticate.
    """
    from linkedin_poster import LinkedInPoster  # type: ignore[import]

    post_text = _extract_section(body, "Draft Content")
    if not post_text:
        raise ValueError("Approval file is missing a '## Draft Content' section")

    if DRY_RUN:
        logger.info("[DRY_RUN] Would post to LinkedIn (%d chars)", len(post_text))
        return "dry_run"

    # Temporarily override DRY_RUN for the poster since we've already checked it.
    saved_dry_run = os.environ.get("DRY_RUN", "true")
    os.environ["DRY_RUN"] = "false"
    try:
        poster = LinkedInPoster()
        result = poster.post_update(post_text)
    finally:
        os.environ["DRY_RUN"] = saved_dry_run

    urn = result.get("id", "unknown") if isinstance(result, dict) else str(result)
    logger.info("LinkedIn post published -- id=%s", urn)
    return f"posted:{urn}"


# ---------------------------------------------------------------------------
# Manual platform handlers (WhatsApp / Discord)
# ---------------------------------------------------------------------------


def _handle_manual_reply(fm: dict[str, str], body: str, platform: str) -> str:
    """Log manual reply instructions for platforms without auto-send support.

    The orchestrator cannot send WhatsApp or Discord messages automatically.
    This function extracts the reply text and prints clear instructions
    for the owner to send manually.

    Args:
        fm: Parsed frontmatter dict with channel/contact context fields.
        body: Markdown body text containing a ``## Draft Reply`` section.
        platform: Display name for the platform (``"Discord"`` or ``"WhatsApp"``).

    Returns:
        Always ``"manual_required"``.
    """
    reply_text = _extract_section(body, "Draft Reply") or _extract_section(
        body, "Message"
    )
    channel = fm.get("channel", fm.get("contact", "(unknown)"))
    author = fm.get("author", fm.get("contact", "(unknown)"))

    separator = "-" * 62
    manual_block = (
        f"\n{separator}\n"
        f"  ACTION REQUIRED -- Manual {platform} Reply\n"
        f"  Platform : {platform}\n"
        f"  Channel  : {channel}\n"
        f"  From     : {author}\n"
        f"\n  Reply text to send:\n\n"
        f"{reply_text}\n\n"
        f"  Please send this reply manually in {platform}.\n"
        f"{separator}\n"
    )
    logger.info(manual_block)
    return "manual_required"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def _write_audit_log(
    action_type: str,
    target: str,
    approved_file: str,
    action: str,
    result: str,
) -> None:
    """Append a structured audit log entry to today's JSON log file.

    Args:
        action_type: Descriptor string (e.g. ``"send_email_executed"``).
        target: Target of the action (email address, platform name, etc.).
        approved_file: Filename of the processed approval file.
        action: Raw action field value from frontmatter.
        result: Outcome string (``"sent:<id>"``, ``"dry_run"``, ``"error"``, etc.).
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.json"

    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "Orchestrator",
        "target": target,
        "parameters": {
            "approved_file": approved_file,
            "action": action,
        },
        "approval_status": "approved",
        "approved_by": "human",
        "result": result,
    }

    entries: list[dict] = []
    if log_file.exists():
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append(entry)
    log_file.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# File move: Approved → Done
# ---------------------------------------------------------------------------


def _move_to_done(file_path: Path, content: str) -> None:
    """Update the file's status to done and move it from Approved/ to Done/.

    Args:
        file_path: Absolute path to the file currently in Approved/.
        content: Original file content (frontmatter + body) to be updated.
    """
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    done_path = DONE_DIR / file_path.name

    updated = re.sub(
        r"^(status:\s*)\S+",
        r"\1done",
        content,
        flags=re.MULTILINE,
        count=1,
    )

    if DRY_RUN:
        logger.info("[DRY_RUN] Would move %s -> Done/", file_path.name)
        return

    done_path.write_text(updated, encoding="utf-8")
    file_path.unlink()
    logger.info("Moved %s -> Done/", file_path.name)


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def _process_file(file_path: Path) -> None:
    """Process a single approved file end-to-end.

    Reads the file, dispatches the action, writes the audit log, and moves
    the file to Done/. Catches and logs all exceptions so one bad file
    cannot crash the orchestrator loop.

    Args:
        file_path: Absolute path to an *.md file in Approved/.
    """
    logger.info("Processing: %s", file_path.name)

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Cannot read file: %s -- skipping", file_path.name)
        return

    fm, body = _parse_frontmatter(content)

    if not fm:
        logger.warning("No frontmatter in %s -- skipping", file_path.name)
        return

    action = fm.get("action", "")
    if not action:
        logger.warning("No 'action' field in %s -- skipping", file_path.name)
        return

    # --- Expiry check ---
    if _is_expired(fm):
        logger.warning("Approval expired: %s -- skipping", file_path.name)
        _write_audit_log(
            action_type=f"{action}_skipped",
            target=fm.get("to", fm.get("contact", "unknown")),
            approved_file=file_path.name,
            action=action,
            result="skipped_expired",
        )
        return

    # --- Dispatch ---
    result = "unknown"
    target = "unknown"

    try:
        if action == "send_email":
            target = fm.get("to", "unknown")
            result = _send_email(fm, body)

        elif action == "post_linkedin":
            target = "linkedin"
            result = _post_linkedin(fm, body)

        elif action == "discord_reply":
            target = fm.get("channel", "discord")
            result = _handle_manual_reply(fm, body, "Discord")

        elif action == "whatsapp_reply":
            target = fm.get("contact", "whatsapp")
            result = _handle_manual_reply(fm, body, "WhatsApp")

        elif action == "draft_email":
            # Draft creation is handled by the email-send MCP server when Claude
            # Code is open. Log this as a manual task for when Claude is available.
            target = fm.get("to", "unknown")
            logger.info(
                "action=draft_email detected in %s -- "
                "open Claude Code and run the approval-executing skill to create the draft.",
                file_path.name,
            )
            result = "manual_required"

        else:
            logger.warning("Unknown action %r in %s -- skipping", action, file_path.name)
            return

    except Exception:
        logger.exception("Error executing action %r for %s", action, file_path.name)
        result = "error"

    # --- Audit log ---
    _write_audit_log(
        action_type=f"{action}_executed",
        target=target,
        approved_file=file_path.name,
        action=action,
        result=result,
    )

    # --- Move to Done/ ---
    _move_to_done(file_path, content)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_loop() -> None:
    """Poll Approved/ and dispatch all pending approval files.

    Runs indefinitely until interrupted by Ctrl+C. Catches and logs scan-level
    errors so transient failures (e.g. a locked file) don't stop the loop.
    """
    logger.info(
        "Orchestrator started -- vault=%s interval=%ds dry_run=%s",
        VAULT_ROOT,
        CHECK_INTERVAL,
        DRY_RUN,
    )

    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            try:
                pending = sorted(APPROVED_DIR.glob("*.md"))
                if pending:
                    logger.info("Found %d file(s) in Approved/", len(pending))
                    for file_path in pending:
                        _process_file(file_path)
                else:
                    logger.debug("Approved/ is empty -- sleeping %ds", CHECK_INTERVAL)
            except Exception:
                logger.exception("Error during Approved/ scan")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Orchestrator stopped by user (KeyboardInterrupt)")


if __name__ == "__main__":
    run_loop()
