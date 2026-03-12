# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the absolute path to the backend directory where .env lives
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_file_path = os.path.join(backend_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "SRM AI SETU"
    DATABASE_URL: str = "postgresql://postgres:0412@localhost:5432/AI%20SETU"
    SECRET_KEY: str = "your-secret-key-for-development!"  # Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    encryption_key: str = "default_placeholder_if_missing"
    google_api_key: str = "default_placeholder_if_missing"

    # SMTP Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        extra="allow"
    )

settings = Settings()
