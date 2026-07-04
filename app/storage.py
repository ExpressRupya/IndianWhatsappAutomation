import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from .config import NEWS_LOG_FILE

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "date_found", "published_date", "company_matched", "category",
    "title", "source", "link", "score", "matched_keywords", "sent_to_whatsapp",
]

NEWS_JSON_FILE = NEWS_LOG_FILE.with_suffix(".json")


def save_articles(articles: list[dict]):
    write_header = not NEWS_LOG_FILE.exists()
    with open(NEWS_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        for art in articles:
            row = {
                "date_found": datetime.now().isoformat(),
                "published_date": art.get("iso_date") or art.get("date", ""),
                "company_matched": art.get("company_matched", ""),
                "category": art.get("category", "general"),
                "title": art["title"],
                "source": art.get("source", ""),
                "link": art["link"],
                "score": art.get("score", 0),
                "matched_keywords": "; ".join(art.get("matched_keywords", [])),
                "sent_to_whatsapp": "no",
            }
            writer.writerow(row)
    logger.info(f"Saved {len(articles)} articles to {NEWS_LOG_FILE}")

    all_records = []
    if NEWS_LOG_FILE.exists():
        import pandas as pd
        df = pd.read_csv(NEWS_LOG_FILE)
        all_records = df.to_dict(orient="records")

    output = {
        "meta": {
            "total_articles": len(all_records),
            "companies_covered": len(set(r.get("company_matched", "") for r in all_records)),
            "last_run": datetime.now().isoformat(),
        },
        "articles": all_records,
    }
    NEWS_JSON_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info(f"Saved {len(all_records)} articles to {NEWS_JSON_FILE}")
