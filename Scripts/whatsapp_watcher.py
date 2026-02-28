"""WhatsApp watcher for the AI Employee vault.

Monitors WhatsApp Web for unread messages using Playwright with a persistent
browser context. On first run, opens a headful browser so the user can scan
the QR code. Subsequent runs are headless.

Creates WHATSAPP_*.md files in Needs_Action/ for messages that match the
configured keyword filter.

Usage:
    uv run python Scripts/whatsapp_watcher.py

First run (QR setup):
    The browser window will open automatically. Scan the QR code shown on
    web.whatsapp.com, wait for your chats to finish loading, then press
    Enter in this terminal.

Environment variables (or set in .env):
    VAULT_PATH                Root path to the vault (default: parent of Scripts/)
    WHATSAPP_SESSION_PATH     Playwright persistent context dir
                              (default: Scripts/.whatsapp_session)
    WHATSAPP_KEYWORDS         CSV of trigger keywords
                              (default: urgent,asap,invoice,payment,help,question,project)
    WHATSAPP_CHECK_INTERVAL   Seconds between polls (default: 30)
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

_DEFAULT_KEYWORDS = "urgent,asap,invoice,payment,help,question,project"
_DEFAULT_INTERVAL = 30
_WHATSAPP_URL = "https://web.whatsapp.com"
_CHAT_LIST_TIMEOUT_MS = 45_000

# Keywords that escalate priority to "high"
_URGENT_KEYWORDS = frozenset({"urgent", "asap", "emergency", "help", "payment", "invoice"})


class WhatsAppWatcher(BaseWatcher):
    """Monitors WhatsApp Web for unread messages and creates vault action files.

    Uses Playwright with a persistent browser context to preserve the WhatsApp
    Web session between runs. On first launch (no session exists), opens a
    headful browser for QR code scanning. Subsequent runs use headless mode.

    Tracks processed messages by contact→preview_hash in a JSON state file to
    avoid creating duplicate action files for the same message.

    Attributes:
        session_path: Path to the Playwright persistent context directory.
        keywords: Set of lowercase trigger keywords. Empty means accept all.
        state_file: Path to the JSON state file.
        _processed: Dict mapping contact name to last processed preview hash.
    """

    def __init__(
        self,
        vault_path: str | Path,
        session_path: str | Path | None = None,
        keywords: str | None = None,
        check_interval: int | None = None,
    ) -> None:
        """Initialise the WhatsApp watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            session_path: Playwright persistent context directory. Falls back to
                ``WHATSAPP_SESSION_PATH`` env var or ``Scripts/.whatsapp_session``.
            keywords: CSV string of trigger keywords. Falls back to
                ``WHATSAPP_KEYWORDS`` env var or the default keyword set.
            check_interval: Seconds between polls. Falls back to
                ``WHATSAPP_CHECK_INTERVAL`` env var or 30.
        """
        script_dir = Path(__file__).parent

        resolved_interval = check_interval or int(
            os.environ.get("WHATSAPP_CHECK_INTERVAL", _DEFAULT_INTERVAL)
        )
        super().__init__(vault_path, check_interval=resolved_interval)

        self.session_path = Path(
            session_path
            or os.environ.get(
                "WHATSAPP_SESSION_PATH", str(script_dir / ".whatsapp_session")
            )
        )

        raw_keywords = keywords or os.environ.get("WHATSAPP_KEYWORDS", _DEFAULT_KEYWORDS)
        self.keywords = {kw.strip().lower() for kw in raw_keywords.split(",") if kw.strip()}

        self.state_file = script_dir / ".whatsapp_watcher_state.json"
        self._processed: dict[str, str] = self._load_state()

        self.logger.info(
            "WhatsApp watcher initialised (session=%s, keywords=%s, interval=%ds)",
            self.session_path,
            sorted(self.keywords) or "ALL",
            self.check_interval,
        )

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> dict[str, str]:
        """Load processed message state from disk.

        Returns:
            Dict mapping contact name → last processed preview hash (12-char MD5).
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                loaded: dict[str, str] = data.get("processed", {})
                self.logger.debug(
                    "Loaded WhatsApp state: %d contact(s) tracked", len(loaded)
                )
                return loaded
            except (json.JSONDecodeError, KeyError):
                self.logger.warning("Corrupted WhatsApp state file — starting fresh")
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
        """Navigate to WhatsApp Web and wait for the user to scan the QR code.

        Blocks until the user presses Enter in the terminal.

        Args:
            page: Playwright Page object from the headful context.

        Returns:
            True if setup completed, False on error.
        """
        try:
            page.goto(_WHATSAPP_URL)
            self.logger.info("=" * 60)
            self.logger.info("FIRST RUN — WhatsApp Web QR Code Setup")
            self.logger.info("1. A browser window has opened.")
            self.logger.info("2. Scan the QR code shown at web.whatsapp.com")
            self.logger.info("3. Wait for your chats to finish loading")
            self.logger.info("4. Press Enter here to continue")
            self.logger.info("=" * 60)
            input("\nPress Enter after your chats have loaded: ")
            self.logger.info("QR scan confirmed — session saved to: %s", self.session_path)
            return True
        except Exception:
            self.logger.exception("Error during first-run QR setup")
            return False

    def _wait_for_chats(self, page) -> bool:
        """Navigate to WhatsApp Web and wait for the chat list to appear.

        If the chat list fails to load (session expired), logs a warning
        and returns False so the caller can trigger a re-authentication.

        Args:
            page: Playwright Page object.

        Returns:
            True if chat list loaded, False on timeout/error.
        """
        try:
            page.goto(_WHATSAPP_URL)
            page.wait_for_selector(
                '[data-testid="chat-list"], #pane-side',
                timeout=_CHAT_LIST_TIMEOUT_MS,
            )
            return True
        except Exception:
            self.logger.warning(
                "WhatsApp Web chat list did not load within %ds "
                "— session may have expired. Delete %s and restart to re-scan QR.",
                _CHAT_LIST_TIMEOUT_MS // 1000,
                self.session_path,
            )
            return False

    # ------------------------------------------------------------------
    # DOM scraping
    # ------------------------------------------------------------------

    def _scrape_unread_chats(self, page) -> list[dict]:
        """Extract unread chat data from the loaded WhatsApp Web page.

        Uses a single JavaScript evaluation to gather all data at once,
        avoiding stale element handle issues. Tries multiple selector
        strategies to handle WhatsApp Web DOM changes across versions.

        Args:
            page: Playwright Page object at web.whatsapp.com with chats loaded.

        Returns:
            List of dicts with ``contact`` (str) and ``preview`` (str) keys.
        """
        try:
            chats: list[dict] = page.evaluate(
                """
                () => {
                    const results = [];

                    // Primary selector: chat list items with unread badge
                    const chatItems = document.querySelectorAll(
                        '[data-testid="cell-frame-container"]'
                    );

                    for (const item of chatItems) {
                        // Detect unread badge — try several known selectors
                        const badge =
                            item.querySelector('[data-testid="icon-unread-count"]') ||
                            item.querySelector('[aria-label*="unread"]') ||
                            item.querySelector('span[data-icon="unread-count"]');

                        if (!badge) continue;

                        // Contact / group name
                        const titleEl =
                            item.querySelector(
                                '[data-testid="cell-frame-title"] span[dir]'
                            ) ||
                            item.querySelector(
                                '[data-testid="cell-frame-title"] span'
                            ) ||
                            item.querySelector('span[title]');

                        // Message preview text
                        const previewEl =
                            item.querySelector('[data-testid="last-msg"] span[dir]') ||
                            item.querySelector('[data-testid="last-msg"]');

                        const contact = titleEl
                            ? (
                                  titleEl.getAttribute("title") ||
                                  titleEl.textContent ||
                                  "Unknown"
                              ).trim()
                            : "Unknown";

                        const preview = previewEl
                            ? previewEl.textContent.trim()
                            : "";

                        // Skip system/unknown entries
                        if (!contact || contact === "Unknown") continue;

                        results.push({ contact, preview });
                    }

                    return results;
                }
                """
            )
        except Exception:
            self.logger.exception("JavaScript evaluation failed during chat scrape")
            return []

        if chats:
            self.logger.debug("Scraped %d unread chat(s) from WhatsApp Web", len(chats))
        else:
            self.logger.debug(
                "No unread chats found (or selectors need updating for this "
                "WhatsApp Web version)"
            )

        return chats

    # ------------------------------------------------------------------
    # BaseWatcher interface
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict]:
        """Open WhatsApp Web, scrape unread chats, and return new keyword matches.

        Launches a Playwright persistent context (headless if session exists,
        headful on first run). Filters results by keyword and deduplicates
        against the state file.

        Returns:
            List of dicts with ``contact``, ``preview``, ``preview_hash``,
            and ``timestamp`` keys for each new actionable message.
        """
        headless = self._session_exists()
        all_chats: list[dict] = []

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
                    # First run — need QR scan
                    success = self._first_run_setup(page)
                    if not success:
                        context.close()
                        return []
                    # After QR scan, page is already on WhatsApp Web
                    # Scrape the freshly loaded chat list
                    all_chats = self._scrape_unread_chats(page)
                else:
                    loaded = self._wait_for_chats(page)
                    if loaded:
                        all_chats = self._scrape_unread_chats(page)

                context.close()

        except Exception:
            self.logger.exception("Playwright error during WhatsApp check")
            return []

        now = datetime.now(timezone.utc).isoformat()
        new_items: list[dict] = []

        for chat in all_chats:
            contact: str = chat.get("contact", "Unknown")
            preview: str = chat.get("preview", "")
            preview_lower = preview.lower()

            # Keyword filter — empty keywords set means accept everything
            if self.keywords and not any(kw in preview_lower for kw in self.keywords):
                self.logger.debug(
                    "Skipping %r — no keyword match (preview=%r)",
                    contact,
                    preview[:60],
                )
                continue

            # Deduplication: skip if this exact preview was already processed
            preview_hash = hashlib.md5(preview.encode("utf-8")).hexdigest()[:12]
            if self._processed.get(contact) == preview_hash:
                self.logger.debug(
                    "Skipping %r — already processed (hash=%s)", contact, preview_hash
                )
                continue

            self.logger.info(
                "New WhatsApp message from %r (preview=%r)", contact, preview[:80]
            )
            new_items.append(
                {
                    "contact": contact,
                    "preview": preview,
                    "preview_hash": preview_hash,
                    "timestamp": now,
                }
            )

        return new_items

    def create_action_file(self, item: dict) -> Path | None:
        """Create a WHATSAPP_*.md action file in Needs_Action/.

        Args:
            item: Dict with ``contact``, ``preview``, ``preview_hash``,
                and ``timestamp`` keys (as returned by ``check_for_updates``).

        Returns:
            Path to the created file, or None if DRY_RUN prevented creation.
        """
        contact: str = item["contact"]
        preview: str = item["preview"]
        preview_hash: str = item["preview_hash"]
        timestamp: str = item["timestamp"]

        # Sanitise contact name for use in filename
        safe_contact = re.sub(r"[^\w\-]", "_", contact).strip("_")[:40]
        dt_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        action_filename = f"WHATSAPP_{safe_contact}_{dt_slug}.md"
        action_path = self.needs_action_path / action_filename

        # Escalate priority for high-urgency keywords
        priority = (
            "high"
            if any(kw in preview.lower() for kw in _URGENT_KEYWORDS)
            else "normal"
        )

        # Escape double quotes in preview for YAML safety
        safe_preview = preview[:200].replace('"', "'")

        content = f"""---
type: whatsapp
status: pending
priority: {priority}
created: {timestamp}
source: whatsapp_watcher
contact: "{contact}"
message_preview: "{safe_preview}"
---

# WhatsApp Message from {contact}

**Contact:** {contact}
**Received:** {timestamp}
**Priority:** {priority}

## Message Preview

{preview}

## Suggested Actions

- [ ] Read full message in WhatsApp
- [ ] Draft reply (use email-drafting skill if formal response needed)
- [ ] Create plan if multi-step work is required
- [ ] Update Dashboard.md
"""

        if self.dry_run:
            self.logger.info(
                "[DRY_RUN] Would create: %s (contact=%r priority=%s)",
                action_path,
                contact,
                priority,
            )
            self._processed[contact] = preview_hash
            self._save_state()
            return None

        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        action_path.write_text(content, encoding="utf-8")
        self.logger.info(
            "Created action file: %s (contact=%r priority=%s)",
            action_path,
            contact,
            priority,
        )

        self._processed[contact] = preview_hash
        self._save_state()
        self._write_audit_log(contact, action_filename, preview, priority, timestamp)

        return action_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_audit_log(
        self,
        contact: str,
        action_file: str,
        preview: str,
        priority: str,
        timestamp: str,
    ) -> None:
        """Append an entry to today's JSON audit log.

        Args:
            contact: WhatsApp contact display name.
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
                "action_type": "whatsapp_message_detected",
                "actor": "WhatsAppWatcher",
                "target": contact,
                "parameters": {
                    "action_file": action_file,
                    "contact": contact,
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
    """Entry point for the WhatsApp watcher script."""
    logging.basicConfig(level=logging.INFO)

    vault_path = os.environ.get(
        "VAULT_PATH",
        str(Path(__file__).resolve().parent.parent),
    )

    watcher = WhatsAppWatcher(vault_path=vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
