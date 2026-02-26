"""Gmail watcher for the AI Employee vault.

Polls Gmail for unread important emails and creates corresponding
action files in Needs_Action/ with proper YAML frontmatter.
Uses the Gmail API with OAuth 2.0 authentication.

Run ``gmail_auth.py`` once first to generate the token file.

Usage:
    uv run python Scripts/gmail_watcher.py

Environment variables (or set in .env):
    VAULT_PATH              Root path to the vault (default: parent of Scripts/)
    GMAIL_CREDENTIALS_PATH  Path to credentials.json (default: Scripts/credentials.json)
    GMAIL_TOKEN_PATH        Path to token.json (default: Scripts/token.json)
    GMAIL_QUERY             Gmail search query (default: is:unread is:important)
    GMAIL_CHECK_INTERVAL    Seconds between polls (default: 120)
    DRY_RUN                 If "true", log actions but do not write files (default: true)
"""

import base64
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from base_watcher import BaseWatcher

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_DEFAULT_QUERY = "is:unread is:important"
_DEFAULT_INTERVAL = 120


class GmailWatcher(BaseWatcher):
    """Watches Gmail for new unread important emails and creates action files.

    Polls the Gmail API on a configurable interval, filtering by a Gmail
    search query. Tracks processed message IDs across restarts via a JSON
    state file to avoid duplicates.

    Attributes:
        credentials_path: Path to credentials.json.
        token_path: Path to the OAuth token file.
        query: Gmail search query used for listing messages.
        processed_ids: Set of message IDs already processed.
        state_file: Path to the JSON state file.
    """

    def __init__(
        self,
        vault_path: str | Path,
        credentials_path: str | Path | None = None,
        token_path: str | Path | None = None,
        query: str | None = None,
        check_interval: int | None = None,
    ) -> None:
        """Initialize the Gmail watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            credentials_path: Path to credentials.json. Falls back to
                ``GMAIL_CREDENTIALS_PATH`` env var or ``Scripts/credentials.json``.
            token_path: Path to token.json. Falls back to ``GMAIL_TOKEN_PATH``
                env var or ``Scripts/token.json``.
            query: Gmail search query. Falls back to ``GMAIL_QUERY`` env var or
                ``is:unread is:important``.
            check_interval: Seconds between polls. Falls back to
                ``GMAIL_CHECK_INTERVAL`` env var or 120.
        """
        script_dir = Path(__file__).parent

        resolved_interval = check_interval or int(
            os.environ.get("GMAIL_CHECK_INTERVAL", _DEFAULT_INTERVAL)
        )
        super().__init__(vault_path, check_interval=resolved_interval)

        # Resolve relative paths against vault root so the script works
        # regardless of which directory it is invoked from.
        def _resolve(raw: str | Path) -> Path:
            p = Path(raw)
            return p if p.is_absolute() else self.vault_path / p

        self.credentials_path = _resolve(
            credentials_path
            or os.environ.get("GMAIL_CREDENTIALS_PATH", script_dir / "credentials.json")
        )
        self.token_path = _resolve(
            token_path
            or os.environ.get("GMAIL_TOKEN_PATH", script_dir / "token.json")
        )
        self.query = query or os.environ.get("GMAIL_QUERY", _DEFAULT_QUERY)

        self.state_file = script_dir / ".gmail_watcher_state.json"
        self.processed_ids: set[str] = self._load_state()

        self._service = self._build_service()

    # ------------------------------------------------------------------
    # Auth & service
    # ------------------------------------------------------------------

    def _load_credentials(self) -> Credentials:
        """Load and refresh OAuth credentials from the token file.

        Returns:
            A valid ``Credentials`` object.

        Raises:
            RuntimeError: If token.json does not exist (user must run gmail_auth.py).
        """
        if not self.token_path.exists():
            raise RuntimeError(
                f"Token file not found: {self.token_path}\n"
                "Run 'uv run python Scripts/gmail_auth.py' to authenticate."
            )

        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                self.logger.info("Refreshing expired Gmail token")
                creds.refresh(Request())
                # Persist refreshed token
                self.token_path.write_text(creds.to_json(), encoding="utf-8")
                self.logger.debug("Refreshed token saved to: %s", self.token_path)
            else:
                raise RuntimeError(
                    "Gmail credentials are invalid and cannot be refreshed.\n"
                    "Run 'uv run python Scripts/gmail_auth.py' to re-authenticate."
                )

        return creds

    def _build_service(self):
        """Build and return the Gmail API service client.

        Returns:
            A Gmail API Resource object.
        """
        creds = self._load_credentials()
        service = build("gmail", "v1", credentials=creds)
        self.logger.info("Gmail API service initialised (query=%r)", self.query)
        return service

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> set[str]:
        """Load the set of previously processed message IDs from disk.

        Returns:
            A set of Gmail message IDs that have already been processed.
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                loaded = set(data.get("processed_ids", []))
                self.logger.debug(
                    "Loaded %d processed message IDs from state", len(loaded)
                )
                return loaded
            except (json.JSONDecodeError, KeyError):
                self.logger.warning("Corrupted state file, starting fresh")
        return set()

    def _save_state(self) -> None:
        """Persist the set of processed message IDs to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(
                {"processed_ids": sorted(self.processed_ids)},
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # BaseWatcher interface
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict]:
        """Poll Gmail API for unread messages matching the configured query.

        Returns:
            A list of dicts with ``id`` and ``threadId`` keys for each new message.
        """
        try:
            result = (
                self._service.users()
                .messages()
                .list(userId="me", q=self.query, maxResults=50)
                .execute()
            )
        except Exception:
            self.logger.exception("Gmail API list() call failed")
            return []

        messages = result.get("messages", [])
        new_messages = [m for m in messages if m["id"] not in self.processed_ids]

        if new_messages:
            self.logger.info("Found %d new message(s) to process", len(new_messages))
        else:
            self.logger.debug("No new messages (query=%r)", self.query)

        return new_messages

    def create_action_file(self, item: dict) -> Path | None:
        """Fetch full message and create an EMAIL_<id>.md action file in Needs_Action/.

        Args:
            item: A dict with at least an ``id`` key (Gmail message ID).

        Returns:
            The Path to the created file, or None if DRY_RUN prevented creation.
        """
        message_id: str = item["id"]
        thread_id: str = item.get("threadId", "")
        now = datetime.now(timezone.utc).isoformat()

        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception:
            self.logger.exception("Failed to fetch message id=%s", message_id)
            return None

        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        sender = headers.get("From", "Unknown")
        recipient = headers.get("To", "Unknown")
        subject = headers.get("Subject", "(no subject)")
        date = headers.get("Date", now)

        body = self._extract_body(msg)

        action_filename = f"EMAIL_{message_id}.md"
        action_path = self.needs_action_path / action_filename

        content = f"""---
type: email
status: pending
priority: high
created: {now}
source: gmail_watcher
message_id: "{message_id}"
thread_id: "{thread_id}"
from: "{sender}"
to: "{recipient}"
subject: "{subject}"
date: "{date}"
---

# Email: {subject}

**From:** {sender}
**To:** {recipient}
**Date:** {date}

## Body

{body}

## Suggested Actions

- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
- [ ] Update Dashboard.md
"""

        if self.dry_run:
            self.logger.info(
                "[DRY_RUN] Would create action file: %s (from=%r subject=%r)",
                action_path,
                sender,
                subject,
            )
            self.processed_ids.add(message_id)
            self._save_state()
            return None

        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        action_path.write_text(content, encoding="utf-8")
        self.logger.info(
            "Created action file: %s (from=%r subject=%r)",
            action_path,
            sender,
            subject,
        )

        self.processed_ids.add(message_id)
        self._save_state()
        self._write_audit_log(message_id, action_filename, sender, subject, now)

        return action_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_body(self, msg: dict) -> str:
        """Extract plain-text body from a Gmail message payload.

        Walks the MIME tree looking for ``text/plain`` parts. Falls back to
        the message snippet if no plain-text part is found.

        Args:
            msg: The full Gmail message dict from the API.

        Returns:
            Decoded plain-text body string.
        """
        payload = msg.get("payload", {})
        body = self._find_plain_text(payload)
        if body:
            return body
        # Fallback: snippet (HTML-stripped preview, up to ~160 chars)
        snippet = msg.get("snippet", "")
        if snippet:
            self.logger.debug("Using snippet as body fallback for message %s", msg.get("id"))
            return snippet
        return "(no body)"

    def _find_plain_text(self, payload: dict) -> str:
        """Recursively search MIME parts for text/plain content.

        Args:
            payload: A Gmail message payload dict (may contain nested ``parts``).

        Returns:
            Decoded plain-text string, or empty string if not found.
        """
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode(
                        "utf-8", errors="replace"
                    )
                except Exception:
                    self.logger.warning("Failed to decode text/plain body part")

        for part in payload.get("parts", []):
            result = self._find_plain_text(part)
            if result:
                return result

        return ""

    def _write_audit_log(
        self,
        message_id: str,
        action_file: str,
        sender: str,
        subject: str,
        timestamp: str,
    ) -> None:
        """Append an entry to today's JSON audit log.

        Args:
            message_id: Gmail message ID.
            action_file: The action file created in Needs_Action/.
            sender: Email sender (From header).
            subject: Email subject line.
            timestamp: ISO 8601 timestamp of the event.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.json"

        self.logs_path.mkdir(parents=True, exist_ok=True)

        entries: list[dict] = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                self.logger.warning("Corrupted log file %s, starting fresh", log_file)

        entries.append(
            {
                "timestamp": timestamp,
                "action_type": "email_detected",
                "actor": "GmailWatcher",
                "target": message_id,
                "parameters": {
                    "action_file": action_file,
                    "from": sender,
                    "subject": subject,
                },
                "approval_status": "not_required",
                "approved_by": None,
                "result": "success",
            }
        )

        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        self.logger.debug("Audit log updated: %s", log_file)


def main() -> None:
    """Entry point for the Gmail watcher script."""
    logging.basicConfig(level=logging.INFO)

    vault_path = os.environ.get(
        "VAULT_PATH",
        str(Path(__file__).resolve().parent.parent),
    )

    watcher = GmailWatcher(vault_path=vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
