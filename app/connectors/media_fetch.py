import requests
from typing import NamedTuple

class MediaPayload(NamedTuple):
    bytes: bytes
    filename: str

class TwilioMediaFetcher:
    def __init__(self, account_sid: str, auth_token: str):
        self.sid = account_sid
        self.token = auth_token

    @staticmethod
    def _guess_ext(ct: str, fallback: str = ".ogg") -> str:
        ct = (ct or "").lower()
        if "mpeg" in ct or "mp3" in ct: return ".mp3"
        if "aac" in ct: return ".aac"
        if "3gpp" in ct or "3gp" in ct: return ".3gp"
        if "wav" in ct: return ".wav"
        if "ogg" in ct or "opus" in ct or "application/ogg" in ct: return ".ogg"
        return fallback

    def fetch(self, form) -> MediaPayload:
        url = form.get("MediaUrl0", "")
        ctype = form.get("MediaContentType0", "") or ""
        r = requests.get(url, auth=(self.sid, self.token), timeout=30)
        r.raise_for_status()
        ext = self._guess_ext(ctype)
        return MediaPayload(bytes=r.content, filename=f"note{ext}")
