# app/connectors/google_auth.py
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Sequence, Optional
import pathlib

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS") or str(pathlib.Path("credentials.json").resolve())
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN") or str(pathlib.Path("token.json").resolve())
FORCE_GOOGLE_REAUTH = os.getenv("FORCE_GOOGLE_REAUTH", "0") == "1"
def get_credentials(*, scopes: Sequence[str], force_reauth: Optional[bool] = None) -> Credentials:
    force_reauth = FORCE_GOOGLE_REAUTH if force_reauth is None else force_reauth
    creds = None
    if not force_reauth and os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token and not force_reauth:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_PATH, scopes=scopes)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds



def _scopes_cover(creds: Credentials, required: Sequence[str]) -> bool:
    try:
        granted = set(creds.scopes or [])
        return set(required).issubset(granted)
    except Exception:
        return False


def _debug_scopes(creds: Credentials):
    try:
        print("Granted scopes:", json.dumps(creds.scopes or [], indent=2))
    except Exception:
        pass
