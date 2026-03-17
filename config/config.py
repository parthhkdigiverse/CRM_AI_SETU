import os

# Global API Configuration
HOST = os.getenv("SRM_HOST", "127.0.0.1")
PORT = int(os.getenv("SRM_PORT", os.getenv("PORT", "8000")))
API_BASE_URL = os.getenv("API_BASE_URL", f"http://{HOST}:{PORT}/api")
