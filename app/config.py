import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
MIN_SCORE = int(os.getenv("MIN_SCORE", "20"))
MAX_DIGEST_ITEMS = int(os.getenv("MAX_DIGEST_ITEMS", "10"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "15"))
MAX_SEND_MESSAGES = int(os.getenv("MAX_SEND_MESSAGES", "0"))
STORAGE_MODE = os.getenv("STORAGE_MODE", "csv")

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.csv"
QUERIES_FILE = DATA_DIR / "queries.csv"
NEWS_LOG_FILE = DATA_DIR / "news_log.csv"
LOG_FILE = LOGS_DIR / "run.log"
