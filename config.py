import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    MURF_API_URL = os.getenv("MURF_API_URL", "https://api.murf.ai/v1")
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # Upload Settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR = "uploads"
    TEMP_DIR = "temp"
    
    # Supported file types
    ALLOWED_EXTENSIONS = {".pdf"}

config = Config() 