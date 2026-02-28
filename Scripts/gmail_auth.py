"""One-time Gmail OAuth 2.0 authentication flow.

Run this script once to authorise the AI Employee to access your Gmail inbox
and send emails. It opens a browser window for the Google consent screen and
writes a token file reused by ``gmail_watcher.py`` and the email-send MCP server.

If you are updating an existing token to add the gmail.send scope, delete
``Scripts/token.json`` first so Google re-prompts for the updated consent.

Usage:
    uv run python Scripts/gmail_auth.py

Environment variables (or set in .env):
    GMAIL_CREDENTIALS_PATH  Path to credentials.json (default: Scripts/credentials.json)
    GMAIL_TOKEN_PATH        Path where token.json will be saved (default: Scripts/token.json)
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    # gmail.send is required by the email-send MCP server.
    # After adding this scope, delete Scripts/token.json and re-run this script
    # to re-authorize — Google only grants new scopes on a fresh consent.
    "https://www.googleapis.com/auth/gmail.send",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [gmail_auth] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_auth_flow(credentials_path: Path, token_path: Path) -> None:
    """Run the OAuth consent flow and save the resulting token.

    Args:
        credentials_path: Path to the credentials.json downloaded from Google Cloud Console.
        token_path: Destination path for the generated token.json.

    Raises:
        FileNotFoundError: If credentials.json does not exist at the given path.
        RuntimeError: If the OAuth flow fails to produce a valid credential.
    """
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at: {credentials_path}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    logger.info("Starting OAuth flow with credentials: %s", credentials_path)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)

    if not creds or not creds.valid:
        raise RuntimeError("OAuth flow completed but credentials are invalid.")

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    logger.info("Token saved to: %s", token_path)
    logger.info("Authentication successful. You can now run gmail_watcher.py.")


def main() -> None:
    """Entry point: read paths from env and run the auth flow."""
    script_dir = Path(__file__).resolve().parent
    vault_root = script_dir.parent  # Scripts/ -> vault root

    def _resolve(raw: str | Path) -> Path:
        p = Path(raw)
        return p if p.is_absolute() else vault_root / p

    credentials_path = _resolve(
        os.environ.get("GMAIL_CREDENTIALS_PATH", script_dir / "credentials.json")
    )
    token_path = _resolve(
        os.environ.get("GMAIL_TOKEN_PATH", script_dir / "token.json")
    )

    try:
        run_auth_flow(credentials_path, token_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        logger.error("Auth flow failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
