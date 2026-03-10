import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Better pathing: Get the directory where config.py is, then go up to /backend
# If your structure is backend/app/core/config.py, you need to go up 2 levels to reach /backend
current_dir = os.path.dirname(os.path.abspath(__file__)) # app/core
backend_dir = os.path.abspath(os.path.join(current_dir, "../../")) # backend
env_file_path = os.path.join(backend_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "SRM AI SETU"
    DATABASE_URL: str = "sqlite:///./crm.db"
    SECRET_KEY: str = "your-secret-key-for-development"  # Change in production!
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

# Add this to help us find it
if __name__ == "__main__":
    print(f"Searching for .env at: {env_file_path}")
    print(f"File exists? {os.path.exists(env_file_path)}")