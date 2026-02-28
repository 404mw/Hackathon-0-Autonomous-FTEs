"""Discord watcher for the AI Employee vault.

Event-driven bot using discord.py that creates DISCORD_*.md files in
Needs_Action/ when:
  - The bot is @mentioned in a monitored server channel, OR
  - A user sends a DM directly to the bot (always captured; no mention needed).

Unlike the polling-based watchers, this bot uses discord.py's websocket
connection. The BaseWatcher polling loop is replaced by bot.run(token).

Setup:
    1. Create a bot at https://discord.com/developers/applications
    2. Enable "Message Content Intent" under Bot → Privileged Gateway Intents
    3. Invite the bot to your server with the "bot" scope + "Read Messages" perm
    4. Copy the bot token to .env as DISCORD_BOT_TOKEN

Usage:
    uv run python Scripts/discord_watcher.py

Environment variables (or set in .env):
    VAULT_PATH              Root path to the vault (default: parent of Scripts/)
    DISCORD_BOT_TOKEN       Bot token from Discord Developer Portal (required)
    DISCORD_CHANNEL_IDS     CSV of channel snowflake IDs where @mentions are
                            watched; empty = watch all channels for mentions
    DISCORD_MONITOR_DMS     Monitor DMs sent to the bot (default: true)
    DRY_RUN                 If "true", log but do not write files (default: true)
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from base_watcher import BaseWatcher

_URGENT_KEYWORDS = frozenset({"urgent", "asap", "emergency", "help", "payment", "invoice"})


class DiscordWatcher(BaseWatcher):
    """Monitors Discord for @mentions and DMs, creating vault action files.

    Trigger rules:
      - Server channel: fires only when the bot is @mentioned in the message.
      - DM: fires on every message sent directly to the bot.

    Extends BaseWatcher but overrides run() to use discord.py's event loop
    instead of the polling loop. check_for_updates() is a no-op; all work
    happens in the on_message event callback.

    Attributes:
        token: Discord bot token.
        channel_ids: Set of channel snowflake IDs where @mentions are watched.
            Empty means watch all channels.
        monitor_dms: Whether to process DMs sent to the bot.
        state_file: Path to JSON state file tracking processed message IDs.
        _processed_ids: Set of Discord message snowflake IDs already handled.
        _bot: The discord.py Bot instance.
    """

    def __init__(
        self,
        vault_path: str | Path,
        token: str | None = None,
        channel_ids: str | None = None,
        monitor_dms: bool | None = None,
    ) -> None:
        """Initialise the Discord watcher.

        Args:
            vault_path: Root path to the AI Employee vault.
            token: Discord bot token. Falls back to DISCORD_BOT_TOKEN env var.
            channel_ids: CSV of channel snowflake IDs where @mentions trigger
                an action file. Falls back to DISCORD_CHANNEL_IDS env var.
                Empty means all channels are watched for mentions.
            monitor_dms: Whether to process DMs. Falls back to
                DISCORD_MONITOR_DMS env var (default: true).
        """
        # check_interval is unused (event-driven) but required by BaseWatcher
        super().__init__(vault_path, check_interval=0)

        self.token: str = token or os.environ.get("DISCORD_BOT_TOKEN", "")
        if not self.token:
            raise RuntimeError(
                "DISCORD_BOT_TOKEN is not set. "
                "Add it to .env or pass token= to DiscordWatcher()."
            )

        raw_channels = channel_ids or os.environ.get("DISCORD_CHANNEL_IDS", "")
        self.channel_ids: set[int] = {
            int(c.strip()) for c in raw_channels.split(",") if c.strip().isdigit()
        }

        dm_env = os.environ.get("DISCORD_MONITOR_DMS", "true")
        self.monitor_dms: bool = (
            monitor_dms if monitor_dms is not None else dm_env.lower() == "true"
        )

        script_dir = Path(__file__).parent
        self.state_file = script_dir / ".discord_watcher_state.json"
        self._processed_ids: set[str] = self._load_state()

        self._bot = self._build_bot()

        self.logger.info(
            "Discord watcher initialised (channels=%s, dms=%s, trigger=mention+dm)",
            sorted(self.channel_ids) or "ALL",
            self.monitor_dms,
        )

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> set[str]:
        """Load already-processed message IDs from disk.

        Returns:
            Set of Discord message snowflake IDs (as strings) already handled.
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                loaded: set[str] = set(data.get("processed_ids", []))
                self.logger.debug("Loaded %d processed Discord message ID(s)", len(loaded))
                return loaded
            except (json.JSONDecodeError, KeyError):
                self.logger.warning("Corrupted Discord state file — starting fresh")
        return set()

    def _save_state(self) -> None:
        """Persist processed message IDs to disk.

        Keeps only the most recent 5 000 IDs to prevent unbounded growth.
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        # Keep last 5000 to cap file size; IDs are lexicographically sortable
        trimmed = sorted(self._processed_ids)[-5000:]
        self.state_file.write_text(
            json.dumps({"processed_ids": trimmed}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Bot construction
    # ------------------------------------------------------------------

    def _build_bot(self) -> commands.Bot:
        """Create and configure the discord.py Bot with required intents.

        Returns:
            A configured discord.py Bot instance with on_message registered.
        """
        intents = discord.Intents.default()
        intents.message_content = True  # required for reading message body
        intents.dm_messages = self.monitor_dms

        bot = commands.Bot(command_prefix="!", intents=intents)

        # Register event handlers as closures so they have access to self
        @bot.event
        async def on_ready() -> None:
            self.logger.info(
                "Discord bot connected as %s (id=%s)", bot.user, bot.user.id if bot.user else "?"
            )

        @bot.event
        async def on_message(message: discord.Message) -> None:
            await self._handle_message(message)

        return bot

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, message: discord.Message) -> None:
        """Process an incoming Discord message event.

        Applies channel, author, keyword, and dedup filters then calls
        create_action_file() for matching messages.

        Args:
            message: The discord.Message object from the on_message event.
        """
        # Never respond to the bot's own messages
        if message.author == self._bot.user:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)

        # Channel filter: monitor DMs if enabled, or only configured channel IDs
        if is_dm:
            if not self.monitor_dms:
                return
        elif self.channel_ids and message.channel.id not in self.channel_ids:
            self.logger.debug(
                "Ignoring message in unmonitored channel %s (%d)",
                message.channel,
                message.channel.id,
            )
            return

        content = message.content.strip()
        if not content:
            return

        # Trigger filter:
        #   Server channel — only act when the bot is @mentioned
        #   DM             — always act (user is already addressing the bot directly)
        if not is_dm and self._bot.user not in message.mentions:
            self.logger.debug(
                "Ignoring message %s from %s — bot not mentioned",
                message.id,
                message.author,
            )
            return

        # Deduplication
        msg_id = str(message.id)
        if msg_id in self._processed_ids:
            self.logger.debug("Ignoring already-processed message %s", msg_id)
            return

        trigger = "dm" if is_dm else "mention"
        self.logger.info(
            "New Discord %s id=%s from %s in %s",
            trigger,
            msg_id,
            message.author,
            message.channel,
        )

        item = {
            "message_id": msg_id,
            "content": content,
            "author": str(message.author),
            "guild": message.guild.name if message.guild else "DM",
            "channel": str(message.channel) if not is_dm else "DM",
            "channel_id": str(message.channel.id),
            "is_dm": is_dm,
            "trigger": trigger,
            "timestamp": message.created_at.astimezone(timezone.utc).isoformat(),
        }

        self.create_action_file(item)

        # React with an emoji to acknowledge the message was received and queued.
        try:
            await message.add_reaction("<a:noted:1477362125436489788>")
        except discord.Forbidden:
            self.logger.warning("No permission to add reaction to message %s", msg_id)
        except discord.HTTPException as exc:
            self.logger.warning("Failed to add reaction to message %s: %s", msg_id, exc)

    # ------------------------------------------------------------------
    # BaseWatcher interface
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict]:
        """No-op — Discord is event-driven; updates arrive via on_message.

        Returns:
            Always an empty list.
        """
        return []

    def run(self) -> None:
        """Start the Discord bot. Blocks until the bot is stopped (Ctrl+C).

        Overrides BaseWatcher.run() — replaces the polling loop with
        discord.py's blocking event loop.
        """
        self.logger.info(
            "Starting DiscordWatcher (dry_run=%s, channels=%s)",
            self.dry_run,
            sorted(self.channel_ids) or "all",
        )
        try:
            self._bot.run(self.token, log_handler=None)
        except KeyboardInterrupt:
            self.logger.info("Discord watcher stopped by user (KeyboardInterrupt)")

    def create_action_file(self, item: dict) -> Path | None:
        """Create a DISCORD_*.md action file in Needs_Action/.

        Args:
            item: Dict with message_id, content, author, guild, channel,
                channel_id, is_dm, trigger, and timestamp keys.

        Returns:
            Path to the created file, or None if DRY_RUN prevented creation.
        """
        message_id: str = item["message_id"]
        content: str = item["content"]
        author: str = item["author"]
        guild: str = item["guild"]
        channel: str = item["channel"]
        trigger: str = item["trigger"]
        timestamp: str = item["timestamp"]

        safe_channel = re.sub(r"[^\w\-]", "_", channel).strip("_")[:40]
        action_filename = f"DISCORD_{safe_channel}_{message_id}.md"
        action_path = self.needs_action_path / action_filename

        priority = (
            "high"
            if any(kw in content.lower() for kw in _URGENT_KEYWORDS)
            else "normal"
        )

        safe_content = content[:200].replace('"', "'")

        file_content = f"""---
type: discord
status: pending
priority: {priority}
created: {timestamp}
source: discord_watcher
trigger: {trigger}
guild: "{guild}"
channel: "{channel}"
author: "{author}"
message_id: "{message_id}"
message_preview: "{safe_content}"
---

# Discord {trigger.upper()} from {author}

**Server:** {guild}
**Channel:** {channel}
**Author:** {author}
**Trigger:** {trigger}
**Received:** {timestamp}
**Priority:** {priority}

## Message Content

{content}

## Suggested Actions

- [ ] Read full thread in Discord
- [ ] Draft reply if response required
- [ ] Create plan if multi-step work is required
- [ ] Update Dashboard.md
"""

        if self.dry_run:
            self.logger.info(
                "[DRY_RUN] Would create: %s (author=%r priority=%s)",
                action_path,
                author,
                priority,
            )
            self._processed_ids.add(message_id)
            self._save_state()
            return None

        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        action_path.write_text(file_content, encoding="utf-8")
        self.logger.info(
            "Created action file: %s (author=%r priority=%s)",
            action_path,
            author,
            priority,
        )

        self._processed_ids.add(message_id)
        self._save_state()
        self._write_audit_log(message_id, action_filename, author, guild, channel, priority, timestamp)

        return action_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_audit_log(
        self,
        message_id: str,
        action_file: str,
        author: str,
        guild: str,
        channel: str,
        priority: str,
        timestamp: str,
    ) -> None:
        """Append an entry to today's JSON audit log.

        Args:
            message_id: Discord message snowflake ID.
            action_file: The action filename created in Needs_Action/.
            author: Discord username of the message author.
            guild: Server name (or "DM").
            channel: Channel name (or "DM").
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
                "action_type": "discord_message_detected",
                "actor": "DiscordWatcher",
                "target": message_id,
                "parameters": {
                    "action_file": action_file,
                    "author": author,
                    "guild": guild,
                    "channel": channel,
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
    """Entry point for the Discord watcher script."""
    logging.basicConfig(level=logging.INFO)

    vault_path = os.environ.get(
        "VAULT_PATH",
        str(Path(__file__).resolve().parent.parent),
    )

    watcher = DiscordWatcher(vault_path=vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
