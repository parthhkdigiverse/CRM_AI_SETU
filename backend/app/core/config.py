import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Better pathing: Get the directory where config.py is, then go up to /backend
# If your structure is backend/app/core/config.py, you need to go up 2 levels to reach /backend
current_dir = os.path.dirname(os.path.abspath(__file__)) # app/core
backend_dir = os.path.abspath(os.path.join(current_dir, "../../")) # backend
env_file_path = os.path.join(backend_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRM AI SETU"
    
    # --- CHANGE THIS ---
    # Remove the "postgresql://user:password..." default. 
    # Making it just 'str' without an '=' makes it REQUIRED in the .env file.
    DATABASE_URL: str 
    
    SECRET_KEY: str = "your-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 
    
    encryption_key: str = "default_placeholder_if_missing"
    google_api_key: str = "default_placeholder_if_missing"

    # SMTP Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""

    # This tells Pydantic exactly where to look
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8", # Good practice to include
        extra="allow"
    )

settings = Settings()

# Add this to help us find it
if __name__ == "__main__":
    print(f"Searching for .env at: {env_file_path}")
    print(f"File exists? {os.path.exists(env_file_path)}")