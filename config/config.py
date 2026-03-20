import os

# Global API Configuration
HOST = os.getenv("SRM_HOST", "127.0.0.1")
PORT = int(os.getenv("SRM_PORT", os.getenv("PORT", "8000")))

# Use the environment variable if provided, otherwise construct it dynamically
_env_api_url = os.getenv("API_BASE_URL")
if _env_api_url:
    API_BASE_URL = _env_api_url
else:
    # If constructive locally, use localhost if 0.0.0.0 is used for binding
    _display_host = "localhost" if HOST == "0.0.0.0" else HOST
    API_BASE_URL = f"http://{_display_host}:{PORT}/api"
