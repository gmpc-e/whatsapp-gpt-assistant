from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    USER_WHATSAPP_NUMBER: str

    GOOGLE_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    # Optional: Google Tasks fallback (if Any.do not configured)
    ENABLE_GOOGLE_TASKS: bool = True

    TIMEZONE: str = "Asia/Jerusalem"
    DEBUG_LOG_PROMPTS: bool = False

    DAILY_DIGEST_HOUR: int = 7
    DAILY_DIGEST_MINUTE: int = 0

    CONFIRM_TTL_MIN: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
