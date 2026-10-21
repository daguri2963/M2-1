import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)
DATABASE = ROOT / 'data/products/products.sqlite3'
POLICY_VERSION = '2026-10-21.1'
CONSENT_VERSION = '2026-10-21.1'
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY', '')
ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:4173,http://localhost:4173,http://127.0.0.1:5173,http://localhost:5173').split(',')
SESSION_TTL = int(os.getenv('SESSION_TTL_SECONDS', '1800'))
AI_TIMEOUT = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '45'))
