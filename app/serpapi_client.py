import requests
import time
import logging
from .config import SERPAPI_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://serpapi.com/search"


def fetch_news(query: str, retries: int = 3) -> list[dict]:
    params = {
        "engine": "google_news",
        "q": query,
        "gl": "in",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            error = data.get("error")
            if error:
                logger.error(f"SerpApi error: {error}")
                return []
            results = []
            for item in data.get("news_results", []):
                results.append({
                    "title": item.get("title", ""),
                    "source": (item.get("source") or {}).get("name", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", ""),
                    "iso_date": item.get("iso_date", ""),
                    "snippet": item.get("snippet", ""),
                })
            return results
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    return []
