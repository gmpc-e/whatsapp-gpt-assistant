"""
Universal Google OAuth helper (user OAuth, token persisted to disk).

Reads:
- settings.GOOGLE_CREDENTIALS_FILE -> path to OAuth client (client_secret*.json)
- settings.GOOGLE_TOKEN_FILE       -> path to store user's token.json

Usage:
    from app.connectors.google_auth import get_credentials
    creds = get_credentials(scopes=["https://www.googleapis.com/auth/tasks"])
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Sequence

from app.config import settings

# google libs are optional at import time (helps tests without deps)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
except Exception:  # pragma: no cover
    Credentials = None  # type: ignore
    Request = None      # type: ignore
    InstalledAppFlow = None  # type: ignore


def _resolve_path(p: str | Path) -> Path:
    p = Path(p)
    if p.is_absolute():
        return p
    # resolve relative to project root (env may pass "token.json", etc.)
    return Path.cwd() / p


def get_credentials(scopes: Sequence[str]) -> "Credentials":
    if Credentials is None or InstalledAppFlow is None:
        raise RuntimeError(
            "google-auth libraries not installed. "
            "pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    token_path = _resolve_path(settings.GOOGLE_TOKEN_FILE)
    creds_path = _resolve_path(settings.GOOGLE_CREDENTIALS_FILE)

    token_path.parent.mkdir(parents=True, exist_ok=True)

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), list(scopes))  # type: ignore[arg-type]

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # silent refresh
            creds.refresh(Request())  # type: ignore[arg-type]
        else:
            # interactive user consent (opens browser once)
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), list(scopes))
            creds = flow.run_local_server(port=0)
        # persist
        token_path.write_text(creds.to_json())

    return creds
