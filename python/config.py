import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5433))
DB_NAME = os.getenv("DB_NAME", "aura")
DB_USER = os.getenv("DB_USER", "aura_user")
DB_PASS = os.getenv("DB_PASS", "aura_pass")

# App
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")