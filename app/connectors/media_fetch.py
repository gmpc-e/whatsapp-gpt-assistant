import requests
import logging
from typing import NamedTuple, Optional

class MediaPayload(NamedTuple):
    bytes: bytes
    filename: str

class TwilioMediaFetcher:
    def __init__(self, account_sid: str, auth_token: str, logger: Optional[logging.Logger] = None):
        self.sid = account_sid
        self.token = auth_token
        self.logger = logger or logging.getLogger(__name__)

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
        if not url:
            self.logger.error("No media URL provided in form")
            raise ValueError("No media URL provided")
        
        ctype = form.get("MediaContentType0", "") or ""
        self.logger.info("Fetching media: %s (type: %s)", url, ctype)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = requests.get(url, auth=(self.sid, self.token), timeout=30)
                r.raise_for_status()
                ext = self._guess_ext(ctype)
                payload = MediaPayload(bytes=r.content, filename=f"note{ext}")
                self.logger.info("Successfully fetched media: %d bytes", len(payload.bytes))
                return payload
            except requests.exceptions.RequestException as e:
                self.logger.warning("Media fetch attempt %d failed: %s", attempt + 1, e)
                if attempt == max_retries - 1:
                    self.logger.error("All media fetch attempts failed")
                    raise ValueError(f"Failed to fetch media after {max_retries} attempts: {e}")
                continue
        
        raise ValueError("Unexpected error in media fetch")
