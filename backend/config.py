import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)
DATABASE = ROOT / 'data/products/products.sqlite3'
POLICY_VERSION = '2026-10-23.2'
CONSENT_VERSION = '2026-10-23.copa.1'
MODEL = os.getenv('COPA_MODEL', 'gpt-5.4')
API_KEY = os.getenv('COPA_API_KEY', '').strip()
BASE_URL = os.getenv('COPA_BASE_URL', 'https://copa.codyssey.kr/v1').rstrip('/')
ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:4173,http://localhost:4173,http://127.0.0.1:5173,http://localhost:5173').split(',')
SESSION_TTL = int(os.getenv('SESSION_TTL_SECONDS', '1800'))
AI_TIMEOUT = float(os.getenv('AI_TIMEOUT_SECONDS', '45'))
