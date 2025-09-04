# app/config.py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TIMEZONE: str = "Asia/Jerusalem"

    # --- OpenAI ---
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"   # allow override via .env
    # If you added web search connector, you can keep a toggle here:
    ENABLE_WEB_SEARCH: bool = True

    # --- Twilio / WhatsApp ---
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    USER_WHATSAPP_NUMBER: str

    # --- Google ---
    GOOGLE_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    # Google Tasks
    GOOGLE_AUTH_TYPE: str = "service_account"  # or "user"
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = None  # raw json or a path to the json
    GOOGLE_USER_TOKEN_JSON: str | None = None       # if using user creds
    GTASKS_TASKLIST_NAME: str = "Tasks"


    # --- Tasks (optional) ---
    ENABLE_GOOGLE_TASKS: bool = True
    ANYDO_USERNAME: Optional[str] = None
    ANYDO_PASSWORD: Optional[str] = None

    # --- App settings ---
    TIMEZONE: str = "Asia/Jerusalem"
    DEBUG_LOG_PROMPTS: bool = False
    LOG_LEVEL: str = "INFO"

    DAILY_DIGEST_HOUR: int = 7
    DAILY_DIGEST_MINUTE: int = 0

    CONFIRM_TTL_MIN: int = 10
    
    OPENAI_RATE_LIMIT_RPM: int = 60
    OPENAI_RATE_LIMIT_TPM: int = 40000

    # Pydantic v2 config: load .env and IGNORE unknown keys
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
