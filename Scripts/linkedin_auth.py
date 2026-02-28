"""LinkedIn OAuth 2.0 authorization script for the AI Employee vault.

Runs the OAuth 2.0 authorization code flow to obtain an access token
for the LinkedIn API. Run this script once before using linkedin_poster.py.

Prerequisites:
    1. Create a LinkedIn App at https://developer.linkedin.com/apps
    2. Add "Sign In with LinkedIn using OpenID Connect" product
       (grants: openid, profile, email scopes)
    3. Add "Share on LinkedIn" product (grants: w_member_social scope)
    4. Under "Auth" settings, add redirect URI: http://localhost:8080/callback
    5. Copy Client ID and Client Secret to .env as:
           LINKEDIN_CLIENT_ID=<your-client-id>
           LINKEDIN_CLIENT_SECRET=<your-client-secret>

Usage:
    uv run python Scripts/linkedin_auth.py

After running, the token is saved to Scripts/.linkedin_token.json.
Copy LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN into your .env.
"""

import http.server
import json
import logging
import os
import secrets
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
_REDIRECT_URI = "http://localhost:8080/callback"
_SCOPES = "openid profile email w_member_social"

# Shared state captured by the callback handler
_auth_code: str | None = None
_auth_error: str | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """One-shot HTTP handler that captures the OAuth 2.0 callback code."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle the GET request from LinkedIn's redirect."""
        global _auth_code, _auth_error  # noqa: PLW0603
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _auth_code = params["code"][0]
            body = (
                b"<html><body><h2>Authorization successful!"
                b" You may close this tab.</h2></body></html>"
            )
        elif "error" in params:
            _auth_error = params.get("error_description", ["Unknown error"])[0]
            body = f"<html><body><h2>Error: {_auth_error}</h2></body></html>".encode()
        else:
            body = b"<html><body><h2>Unexpected response. Please retry.</h2></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Suppress default HTTP server request logging."""


def _serve_one_request(server: http.server.HTTPServer) -> None:
    """Handle exactly one HTTP request then close the server."""
    server.handle_request()
    server.server_close()


def main() -> None:
    """Run the LinkedIn OAuth 2.0 authorization code flow."""
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.error(
            "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env.\n"
            "Create a LinkedIn App at https://developer.linkedin.com/apps first,\n"
            "then add both 'Sign In with LinkedIn using OpenID Connect' and\n"
            "'Share on LinkedIn' products to get all required scopes."
        )
        return

    state = secrets.token_urlsafe(16)
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _REDIRECT_URI,
        "state": state,
        "scope": _SCOPES,
    }
    auth_url = f"{_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    # Start local callback server in background thread
    server = http.server.HTTPServer(("localhost", 8080), _CallbackHandler)
    thread = threading.Thread(target=_serve_one_request, args=(server,), daemon=True)
    thread.start()

    logger.info("Opening browser for LinkedIn authorization...")
    logger.info("If the browser does not open automatically, visit:")
    logger.info("  %s", auth_url)
    webbrowser.open(auth_url)

    thread.join(timeout=120)

    if _auth_error:
        logger.error("Authorization failed: %s", _auth_error)
        return

    if not _auth_code:
        logger.error("No authorization code received (timed out after 120 s). Please retry.")
        return

    logger.info("Authorization code received. Exchanging for access token...")

    token_resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _auth_code,
            "redirect_uri": _REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    token_resp.raise_for_status()
    token_data: dict = token_resp.json()
    access_token: str = token_data["access_token"]
    logger.info("Access token obtained (expires_in=%s s).", token_data.get("expires_in"))

    # Fetch person ID via OpenID Connect userinfo endpoint
    userinfo_resp = requests.get(
        _USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    userinfo_resp.raise_for_status()
    userinfo: dict = userinfo_resp.json()
    person_id: str = userinfo.get("sub", "")
    person_urn: str = f"urn:li:person:{person_id}"
    person_name: str = userinfo.get("name", "")

    logger.info("Person name: %s", person_name)
    logger.info("Person URN: %s", person_urn)

    # Save token data to file
    script_dir = Path(__file__).parent
    token_file = script_dir / ".linkedin_token.json"
    token_file.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "expires_in": token_data.get("expires_in"),
                "person_urn": person_urn,
                "person_name": person_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info("Token saved to: %s", token_file)
    logger.info("")
    logger.info("Add these values to your .env file:")
    logger.info("  LINKEDIN_ACCESS_TOKEN=%s", access_token)
    logger.info("  LINKEDIN_PERSON_URN=%s", person_urn)


if __name__ == "__main__":
    main()
