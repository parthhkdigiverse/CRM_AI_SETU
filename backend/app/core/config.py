import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the absolute path to the backend directory where .env lives
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_file_path = os.path.join(backend_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRM AI SETU"
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    SECRET_KEY: str = "your-secret-key-for-development"  # Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    encryption_key: str = "default_placeholder_if_missing"
    google_api_key: str = "default_placeholder_if_missing"

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        extra="allow"
    )

settings = Settings()
