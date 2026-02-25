"""Filesystem watcher for the AI Employee vault.

Monitors the Inbox/ folder for new files and creates corresponding
action files in Needs_Action/ with proper YAML frontmatter.
Uses the watchdog library for efficient filesystem event detection
with a polling fallback.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from base_watcher import BaseWatcher


class _InboxEventHandler(FileSystemEventHandler):
    """Watchdog event handler that collects new files in Inbox/."""

    def __init__(self) -> None:
        """Initialize the event handler with an empty event queue."""
        super().__init__()
        self.new_files: list[Path] = []

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events.

        Args:
            event: The filesystem event triggered by a new file.
        """
        if not event.is_directory:
            self.new_files.append(Path(event.src_path))


class FilesystemWatcher(BaseWatcher):
    """Watches Inbox/ for new files and creates action files in Needs_Action/.

    Uses the watchdog library's Observer for real-time filesystem monitoring.
    Tracks processed files to avoid duplicates across restarts via a
    JSON state file.

    Attributes:
        processed_files: Set of filenames already processed.
        state_file: Path to the JSON file tracking processed filenames.
    """

    def __init__(
        self,
        vault_path: str | Path,
        check_interval: int = 5,
    ) -> None:
        """Initialize the filesystem watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            check_interval: Seconds between polling checks. Defaults to 5.
        """
        super().__init__(vault_path, check_interval)

        self.state_file = self.vault_path / "Scripts" / ".fs_watcher_state.json"
        self.processed_files: set[str] = self._load_state()

        self._event_handler = _InboxEventHandler()
        self._observer = Observer()
        self._observer.schedule(
            self._event_handler, str(self.inbox_path), recursive=False
        )

    def _load_state(self) -> set[str]:
        """Load the set of previously processed filenames from disk.

        Returns:
            A set of filenames that have already been processed.
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                loaded = set(data.get("processed_files", []))
                self.logger.debug("Loaded %d processed files from state", len(loaded))
                return loaded
            except (json.JSONDecodeError, KeyError):
                self.logger.warning("Corrupted state file, starting fresh")
        return set()

    def _save_state(self) -> None:
        """Persist the set of processed filenames to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(
                {"processed_files": sorted(self.processed_files)},
                indent=2,
            ),
            encoding="utf-8",
        )

    def check_for_updates(self) -> list[dict]:
        """Check for new files in Inbox/ via watchdog events and directory scan.

        Combines watchdog events with a directory scan to catch files
        that may have been added before the observer started.

        Returns:
            A list of dicts with 'name' and 'path' keys for each new file.
        """
        new_items: list[dict] = []

        # Collect watchdog events
        event_files = list(self._event_handler.new_files)
        self._event_handler.new_files.clear()

        # Also scan the directory for any files missed by events
        scan_files = [
            f for f in self.inbox_path.iterdir() if f.is_file() and f.name != ".gitkeep"
        ]

        # Merge both sources, deduplicating by filename
        all_files: dict[str, Path] = {}
        for f in event_files + scan_files:
            all_files[f.name] = f

        for name, path in all_files.items():
            if name not in self.processed_files:
                new_items.append({"name": name, "path": str(path)})
                self.logger.info("New file detected: %s", name)

        return new_items

    def create_action_file(self, item: dict) -> Path | None:
        """Create a FILE_<name>.md action file in Needs_Action/.

        Args:
            item: A dict with 'name' and 'path' keys.

        Returns:
            The Path to the created file, or None if DRY_RUN prevented creation.
        """
        filename = item["name"]
        source_path = Path(item["path"])
        now = datetime.now(timezone.utc).isoformat()

        # Sanitize filename for the action file
        safe_name = filename.replace(" ", "_")
        action_filename = f"FILE_{safe_name}.md"
        action_path = self.needs_action_path / action_filename

        # Build frontmatter and content
        file_size = source_path.stat().st_size if source_path.exists() else 0
        file_ext = source_path.suffix.lower()

        content = f"""---
type: file_drop
status: pending
priority: normal
created: {now}
source: filesystem_watcher
original_filename: "{filename}"
original_path: "{source_path}"
file_size_bytes: {file_size}
file_extension: "{file_ext}"
---

# File Drop: {filename}

A new file was detected in the Inbox.

## Details

- **Filename:** {filename}
- **Extension:** {file_ext}
- **Size:** {file_size} bytes
- **Detected at:** {now}
- **Source path:** {source_path}

## Suggested Actions

- [ ] Review file contents
- [ ] Categorize and route to appropriate folder
- [ ] Update Dashboard.md
"""

        if self.dry_run:
            self.logger.info("[DRY_RUN] Would create action file: %s", action_path)
            self.processed_files.add(filename)
            self._save_state()
            return None

        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        action_path.write_text(content, encoding="utf-8")
        self.logger.info("Created action file: %s", action_path)

        self.processed_files.add(filename)
        self._save_state()

        self._write_audit_log(filename, action_filename, now)

        return action_path

    def _write_audit_log(
        self, source_file: str, action_file: str, timestamp: str
    ) -> None:
        """Append an entry to today's audit log.

        Args:
            source_file: The original filename from Inbox/.
            action_file: The action file created in Needs_Action/.
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
                "action_type": "file_detected",
                "actor": "FilesystemWatcher",
                "target": source_file,
                "parameters": {"action_file": action_file},
                "approval_status": "not_required",
                "approved_by": None,
                "result": "success",
            }
        )

        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        self.logger.debug("Audit log updated: %s", log_file)

    def run(self) -> None:
        """Start the filesystem watcher with watchdog observer.

        Overrides BaseWatcher.run() to start/stop the watchdog observer
        alongside the polling loop.
        """
        self.logger.info("Starting FilesystemWatcher on: %s", self.inbox_path)
        self._observer.start()
        try:
            super().run()
        finally:
            self._observer.stop()
            self._observer.join()
            self.logger.info("FilesystemWatcher observer stopped")


def main() -> None:
    """Entry point for the filesystem watcher script."""
    logging.basicConfig(level=logging.INFO)

    vault_path = os.environ.get(
        "VAULT_PATH",
        str(Path(__file__).resolve().parent.parent),
    )

    watcher = FilesystemWatcher(vault_path=vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
