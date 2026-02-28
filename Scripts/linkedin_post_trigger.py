"""LinkedIn post trigger for the AI Employee vault.

Creates a ``LINKEDIN_POST_TRIGGER_<YYYY-MM-DD>.md`` file in Needs_Action/,
signalling the vault-triaging → linkedin-posting skill chain to draft and
submit a LinkedIn post for human approval.

Designed to run on a schedule (Mon/Wed/Fri at 09:00) via Windows Task
Scheduler or PM2. Idempotent — if a trigger file already exists for today
it exits without creating a duplicate.

Usage:
    uv run python Scripts/linkedin_post_trigger.py

Environment variables (or set in .env):
    VAULT_PATH  Root path to vault (default: parent of Scripts/)
    DRY_RUN     If "true", log without creating the file (default: true)
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
VAULT_ROOT = Path(os.environ.get("VAULT_PATH", str(_SCRIPTS_DIR.parent)))
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [linkedin-trigger] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trigger file template
# ---------------------------------------------------------------------------

_TRIGGER_TEMPLATE = """\
---
type: linkedin_trigger
status: pending
priority: normal
created: {created}
source: task_scheduler
schedule: Mon/Wed/Fri 09:00
---

# LinkedIn Post Trigger

Scheduled time to generate a LinkedIn post.
Invoke the `linkedin-posting` skill to draft a post for human approval.

## Suggested Topics

- Recent project milestone or delivery
- Insight or lesson from this week's work
- Industry observation relevant to the business
- Progress update on the AI Employee Vault hackathon

## Context

- Owner: 404MW
- Business goals: see Business_Goals.md
- Tone: professional, first-person, conversational
- Avoid: AI filler phrases, bullet-point-only posts, emojis overload
- Length: 150–300 words across 3–5 short paragraphs
"""

# ---------------------------------------------------------------------------
# Trigger creation
# ---------------------------------------------------------------------------


def create_trigger_file() -> Path | None:
    """Create a LinkedIn post trigger file in Needs_Action/.

    Checks for an existing trigger file for today before writing.

    Returns:
        Path to the created (or already existing) file, or None if DRY_RUN
        prevented creation.
    """
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    filename = f"LINKEDIN_POST_TRIGGER_{date_str}.md"
    target = NEEDS_ACTION_DIR / filename

    if target.exists():
        logger.info("Trigger file already exists for today: %s — skipping", filename)
        return target

    content = _TRIGGER_TEMPLATE.format(created=now.isoformat())

    if DRY_RUN:
        logger.info("[DRY_RUN] Would create trigger file: %s", target)
        return None

    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    logger.info("Created LinkedIn post trigger: %s", target)
    return target


if __name__ == "__main__":
    create_trigger_file()
