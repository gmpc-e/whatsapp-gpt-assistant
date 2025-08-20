import io

class OpenAIWhisperConnector:
    def __init__(self, openai_client):
        self.client = openai_client

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        f = io.BytesIO(audio_bytes)
        f.name = filename
        result = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
        return (result.text or "").strip()
