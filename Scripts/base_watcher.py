"""Base watcher abstract class for the AI Employee vault.

All watchers (filesystem, email, WhatsApp, etc.) must extend this class.
Provides common functionality: vault path management, logging, DRY_RUN
support, and a main run loop with error handling.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path


class BaseWatcher(ABC):
    """Abstract base class for all vault watchers.

    Attributes:
        vault_path: Root path to the AI Employee vault.
        check_interval: Seconds between polling checks.
        dry_run: If True, log actions but do not write files.
        logger: Logger instance for this watcher.
    """

    def __init__(
        self,
        vault_path: str | Path,
        check_interval: int = 10,
    ) -> None:
        """Initialize the base watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            check_interval: Seconds between polling checks. Defaults to 10.
        """
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        self.dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

        self.inbox_path = self.vault_path / "Inbox"
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.logs_path = self.vault_path / "Logs"

        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()

        if self.dry_run:
            self.logger.info("DRY_RUN mode is ENABLED — no files will be written")

    def _setup_logging(self) -> None:
        """Configure logging with console and file handlers."""
        if self.logger.handlers:
            return

        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        self.logs_path.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_path / "watcher.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

    @abstractmethod
    def check_for_updates(self) -> list[dict]:
        """Check for new items to process.

        Returns:
            A list of dicts, each representing a new item to process.
            The exact schema depends on the concrete watcher.
        """

    @abstractmethod
    def create_action_file(self, item: dict) -> Path | None:
        """Create a markdown action file in Needs_Action/ for the given item.

        Args:
            item: A dict representing the item to create an action file for.

        Returns:
            The Path to the created file, or None if DRY_RUN prevented creation.
        """

    def run(self) -> None:
        """Main loop: poll for updates and create action files.

        Runs indefinitely until interrupted. Catches and logs all exceptions
        to prevent the watcher from crashing on transient errors.
        """
        self.logger.info(
            "Starting %s (interval=%ds, dry_run=%s)",
            self.__class__.__name__,
            self.check_interval,
            self.dry_run,
        )

        try:
            while True:
                try:
                    items = self.check_for_updates()
                    for item in items:
                        try:
                            self.create_action_file(item)
                        except Exception:
                            self.logger.exception(
                                "Error creating action file for item: %s", item
                            )
                except Exception:
                    self.logger.exception("Error during update check")

                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("Watcher stopped by user (KeyboardInterrupt)")
