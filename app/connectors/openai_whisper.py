import io
import logging
from typing import Optional

class OpenAIWhisperConnector:
    def __init__(self, openai_client, logger: Optional[logging.Logger] = None):
        self.client = openai_client
        self.logger = logger or logging.getLogger(__name__)

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        try:
            f = io.BytesIO(audio_bytes)
            f.name = filename
            result = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                timeout=30
            )
            transcription = (result.text or "").strip()
            self.logger.info("Successfully transcribed audio: %d chars", len(transcription))
            return transcription
        except Exception as e:
            self.logger.error("Whisper transcription failed: %s", e)
            raise
