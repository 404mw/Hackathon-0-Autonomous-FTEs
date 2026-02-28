"""LinkedIn watcher for the AI Employee vault.

Monitors LinkedIn messages using Playwright with a persistent browser context.
On first run, opens a headful browser so the user can log in. Subsequent runs
are headless.

Creates LINKEDIN_*.md files in Needs_Action/ for unread conversations that
match the deduplication filter.

Usage:
    uv run python Scripts/linkedin_watcher.py

First run (login setup):
    A browser window will open automatically. Log into LinkedIn, wait for
    your messages to finish loading, then press Enter in this terminal.

Environment variables (or set in .env):
    VAULT_PATH                Root path to the vault (default: parent of Scripts/)
    LINKEDIN_SESSION_PATH     Playwright persistent context directory
                              (default: Scripts/.linkedin_session)
    LINKEDIN_CHECK_INTERVAL   Seconds between polls (default: 300)
    DRY_RUN                   If "true", log but do not write files (default: true)
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from base_watcher import BaseWatcher

_DEFAULT_INTERVAL = 300
_LINKEDIN_MESSAGES_URL = "https://www.linkedin.com/messaging/"
_MESSAGE_LIST_TIMEOUT_MS = 60_000

# Keywords that escalate priority to "high"
_URGENT_KEYWORDS = frozenset({"urgent", "asap", "emergency", "help", "payment", "invoice"})


class LinkedInWatcher(BaseWatcher):
    """Monitors LinkedIn messaging for unread conversations and creates vault action files.

    Uses Playwright with a persistent browser context to preserve the LinkedIn
    session between runs. On first launch (no session exists), opens a headful
    browser for login. Subsequent runs use headless mode.

    Tracks processed messages by sender→preview_hash in a JSON state file to
    avoid creating duplicate action files for the same message.

    Attributes:
        session_path: Path to the Playwright persistent context directory.
        state_file: Path to the JSON state file.
        _processed: Dict mapping sender name to last processed preview hash.
    """

    def __init__(
        self,
        vault_path: str | Path,
        session_path: str | Path | None = None,
        check_interval: int | None = None,
    ) -> None:
        """Initialise the LinkedIn watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            session_path: Playwright persistent context directory. Falls back to
                LINKEDIN_SESSION_PATH env var or Scripts/.linkedin_session.
            check_interval: Seconds between polls. Falls back to
                LINKEDIN_CHECK_INTERVAL env var or 300.
        """
        script_dir = Path(__file__).parent

        resolved_interval = check_interval or int(
            os.environ.get("LINKEDIN_CHECK_INTERVAL", _DEFAULT_INTERVAL)
        )
        super().__init__(vault_path, check_interval=resolved_interval)

        self.session_path = Path(
            session_path
            or os.environ.get(
                "LINKEDIN_SESSION_PATH", str(script_dir / ".linkedin_session")
            )
        )

        self.state_file = script_dir / ".linkedin_watcher_state.json"
        self._processed: dict[str, str] = self._load_state()

        self.logger.info(
            "LinkedIn watcher initialised (session=%s, interval=%ds)",
            self.session_path,
            self.check_interval,
        )

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> dict[str, str]:
        """Load processed message state from disk.

        Returns:
            Dict mapping sender name → last processed preview hash (12-char MD5).
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                loaded: dict[str, str] = data.get("processed", {})
                self.logger.debug(
                    "Loaded LinkedIn state: %d sender(s) tracked", len(loaded)
                )
                return loaded
            except (json.JSONDecodeError, KeyError):
                self.logger.warning("Corrupted LinkedIn state file — starting fresh")
        return {}

    def _save_state(self) -> None:
        """Persist processed message state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps({"processed": self._processed}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _session_exists(self) -> bool:
        """Return True if a saved Playwright session directory exists and is non-empty."""
        return self.session_path.exists() and any(self.session_path.iterdir())

    def _first_run_setup(self, page) -> bool:
        """Navigate to LinkedIn messaging and wait for the user to log in.

        Blocks until the user presses Enter in the terminal.

        Args:
            page: Playwright Page object from the headful context.

        Returns:
            True if setup completed, False on error.
        """
        try:
            page.goto(_LINKEDIN_MESSAGES_URL)
            self.logger.info("=" * 60)
            self.logger.info("FIRST RUN — LinkedIn Login Setup")
            self.logger.info("1. A browser window has opened.")
            self.logger.info("2. Log into LinkedIn with your credentials.")
            self.logger.info("3. Wait for your messages to fully load.")
            self.logger.info("4. Press Enter here to continue.")
            self.logger.info("=" * 60)
            input("\nPress Enter after your messages have loaded: ")
            self.logger.info("Login confirmed — session saved to: %s", self.session_path)
            return True
        except Exception:
            self.logger.exception("Error during first-run LinkedIn login")
            return False

    def _wait_for_messages(self, page) -> bool:
        """Navigate to LinkedIn messaging and wait for the conversation list.

        If the list fails to load (session expired), logs a warning and returns
        False so the caller can trigger a re-authentication on the next run.

        Args:
            page: Playwright Page object.

        Returns:
            True if the conversation list loaded, False on timeout/error.
        """
        try:
            page.goto(_LINKEDIN_MESSAGES_URL)
            page.wait_for_selector(
                ".msg-conversations-container, [data-test-messaging-list]",
                timeout=_MESSAGE_LIST_TIMEOUT_MS,
            )
            return True
        except Exception:
            self.logger.warning(
                "LinkedIn messaging list did not load within %ds "
                "— session may have expired. Delete %s and restart to re-login.",
                _MESSAGE_LIST_TIMEOUT_MS // 1000,
                self.session_path,
            )
            return False

    # ------------------------------------------------------------------
    # DOM scraping
    # ------------------------------------------------------------------

    def _scrape_unread_conversations(self, page) -> list[dict]:
        """Extract unread conversation data from the LinkedIn messaging page.

        Uses a single JavaScript evaluation to gather all data at once,
        avoiding stale element handle issues. Tries multiple selector
        strategies to handle LinkedIn DOM changes across versions.

        Args:
            page: Playwright Page object at LinkedIn messaging.

        Returns:
            List of dicts with ``sender`` (str) and ``preview`` (str) keys.
        """
        try:
            conversations: list[dict] = page.evaluate(
                """
                () => {
                    const results = [];

                    // Primary: conversation list items (try multiple known selectors)
                    const items = document.querySelectorAll(
                        '.msg-conversation-listitem, ' +
                        '[data-test-messaging-listitem], ' +
                        'li.msg-conversations-container__convo-item'
                    );

                    for (const item of items) {
                        // Detect unread: look for unread count badge or unread-styled snippet
                        const unreadBadge =
                            item.querySelector('.msg-conversation-listitem__unread-count') ||
                            item.querySelector('[data-test-unread-count]') ||
                            item.querySelector('.notification-badge');

                        const unreadSnippet = item.querySelector(
                            '.msg-conversation-listitem__message-snippet--unread, ' +
                            '[class*="unread"]'
                        );

                        if (!unreadBadge && !unreadSnippet) continue;

                        // Sender name
                        const senderEl =
                            item.querySelector(
                                '.msg-conversation-listitem__participant-names span'
                            ) ||
                            item.querySelector('[data-test-messaging-participant-name]') ||
                            item.querySelector('.presence-entity__name');

                        // Message preview
                        const previewEl =
                            item.querySelector(
                                '.msg-conversation-listitem__message-snippet'
                            ) ||
                            item.querySelector('[data-test-messaging-snippet]') ||
                            item.querySelector('.msg-conversation-card__message-snippet');

                        const sender = senderEl
                            ? (
                                  senderEl.getAttribute('title') ||
                                  senderEl.textContent ||
                                  'Unknown'
                              ).trim()
                            : 'Unknown';

                        const preview = previewEl ? previewEl.textContent.trim() : '';

                        if (!sender || sender === 'Unknown') continue;

                        results.push({ sender, preview });
                    }

                    return results;
                }
                """
            )
        except Exception:
            self.logger.exception("JavaScript evaluation failed during LinkedIn scrape")
            return []

        if conversations:
            self.logger.debug(
                "Scraped %d unread LinkedIn conversation(s)", len(conversations)
            )
        else:
            self.logger.debug(
                "No unread LinkedIn conversations found "
                "(or selectors need updating for this LinkedIn version)"
            )

        return conversations

    # ------------------------------------------------------------------
    # BaseWatcher interface
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict]:
        """Open LinkedIn messaging, scrape unread conversations, return new items.

        Launches a Playwright persistent context (headless if session exists,
        headful on first run). Deduplicates against the state file.

        Returns:
            List of dicts with ``sender``, ``preview``, ``preview_hash``,
            and ``timestamp`` keys for each new actionable message.
        """
        headless = self._session_exists()
        all_conversations: list[dict] = []

        try:
            with sync_playwright() as playwright:
                self.session_path.mkdir(parents=True, exist_ok=True)

                context = playwright.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

                page = context.pages[0] if context.pages else context.new_page()

                if not headless:
                    success = self._first_run_setup(page)
                    if not success:
                        context.close()
                        return []
                    all_conversations = self._scrape_unread_conversations(page)
                else:
                    loaded = self._wait_for_messages(page)
                    if loaded:
                        all_conversations = self._scrape_unread_conversations(page)

                context.close()

        except Exception:
            self.logger.exception("Playwright error during LinkedIn check")
            return []

        now = datetime.now(timezone.utc).isoformat()
        new_items: list[dict] = []

        for convo in all_conversations:
            sender: str = convo.get("sender", "Unknown")
            preview: str = convo.get("preview", "")

            preview_hash = hashlib.md5(preview.encode("utf-8")).hexdigest()[:12]
            if self._processed.get(sender) == preview_hash:
                self.logger.debug(
                    "Skipping %r — already processed (hash=%s)", sender, preview_hash
                )
                continue

            self.logger.info(
                "New LinkedIn message from %r (preview=%r)", sender, preview[:80]
            )
            new_items.append(
                {
                    "sender": sender,
                    "preview": preview,
                    "preview_hash": preview_hash,
                    "timestamp": now,
                }
            )

        return new_items

    def create_action_file(self, item: dict) -> Path | None:
        """Create a LINKEDIN_*.md action file in Needs_Action/.

        Args:
            item: Dict with ``sender``, ``preview``, ``preview_hash``,
                and ``timestamp`` keys (as returned by ``check_for_updates``).

        Returns:
            Path to the created file, or None if DRY_RUN prevented creation.
        """
        sender: str = item["sender"]
        preview: str = item["preview"]
        preview_hash: str = item["preview_hash"]
        timestamp: str = item["timestamp"]

        safe_sender = re.sub(r"[^\w\-]", "_", sender).strip("_")[:40]
        dt_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        action_filename = f"LINKEDIN_{safe_sender}_{dt_slug}.md"
        action_path = self.needs_action_path / action_filename

        priority = (
            "high"
            if any(kw in preview.lower() for kw in _URGENT_KEYWORDS)
            else "normal"
        )

        safe_preview = preview[:200].replace('"', "'")

        content = f"""---
type: linkedin
status: pending
priority: {priority}
created: {timestamp}
source: linkedin_watcher
sender: "{sender}"
message_preview: "{safe_preview}"
---

# LinkedIn Message from {sender}

**Sender:** {sender}
**Received:** {timestamp}
**Priority:** {priority}

## Message Preview

{preview}

## Suggested Actions

- [ ] Read full conversation on LinkedIn
- [ ] Draft reply if response required
- [ ] Create plan if multi-step work is required
- [ ] Update Dashboard.md
"""

        if self.dry_run:
            self.logger.info(
                "[DRY_RUN] Would create: %s (sender=%r priority=%s)",
                action_path,
                sender,
                priority,
            )
            self._processed[sender] = preview_hash
            self._save_state()
            return None

        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        action_path.write_text(content, encoding="utf-8")
        self.logger.info(
            "Created action file: %s (sender=%r priority=%s)",
            action_path,
            sender,
            priority,
        )

        self._processed[sender] = preview_hash
        self._save_state()
        self._write_audit_log(sender, action_filename, preview, priority, timestamp)

        return action_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_audit_log(
        self,
        sender: str,
        action_file: str,
        preview: str,
        priority: str,
        timestamp: str,
    ) -> None:
        """Append an entry to today's JSON audit log.

        Args:
            sender: LinkedIn sender display name.
            action_file: The action filename created in Needs_Action/.
            preview: Message preview text (truncated to 200 chars in log).
            priority: Resolved priority string (high/normal).
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
                self.logger.warning("Corrupted log file %s — starting fresh", log_file)

        entries.append(
            {
                "timestamp": timestamp,
                "action_type": "linkedin_message_detected",
                "actor": "LinkedInWatcher",
                "target": sender,
                "parameters": {
                    "action_file": action_file,
                    "sender": sender,
                    "preview": preview[:200],
                    "priority": priority,
                },
                "approval_status": "not_required",
                "approved_by": None,
                "result": "success",
            }
        )

        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        self.logger.debug("Audit log updated: %s", log_file)


def main() -> None:
    """Entry point for the LinkedIn watcher script."""
    logging.basicConfig(level=logging.INFO)

    vault_path = os.environ.get(
        "VAULT_PATH",
        str(Path(__file__).resolve().parent.parent),
    )

    watcher = LinkedInWatcher(vault_path=vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
