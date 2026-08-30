import os
from dotenv import load_dotenv

# Load environment variables from a .env file
# Try multiple possible .env locations
from pathlib import Path
_base = Path(__file__).parent
for _p in [_base/'.env', _base/'..'/'.env', _base/'../..'/'.env', Path('.env'), Path('/home/hitin/AURA/.env')]:
    if _p.exists():
        load_dotenv(_p)
        break

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Database — use Supabase in production, local PostgreSQL in development
if ENVIRONMENT == "production":
    DATABASE_URL = os.getenv("SUPABASE_DB_URL", "")
    DB_HOST = None
    DB_PORT = None
    DB_NAME = None
    DB_USER = None
    DB_PASS = None
else:
    DATABASE_URL = None
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5433))
    DB_NAME = os.getenv("DB_NAME", "aura")
    DB_USER = os.getenv("DB_USER", "aura_user")
    DB_PASS = os.getenv("DB_PASS", "aura_pass")

# App
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")

# OpenRouter AI
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

# Supabase
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

def get_db_connection_string():
    if ENVIRONMENT == "production" and SUPABASE_DB_URL:
        return SUPABASE_DB_URL
    return f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"