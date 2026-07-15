import csv
import json
import logging
from datetime import datetime, date
from pathlib import Path
from .config import NEWS_LOG_FILE

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "date_found", "published_date", "company_matched", "category",
    "title", "source", "link", "score", "matched_keywords", "sent_to_whatsapp",
]

NEWS_JSON_FILE = NEWS_LOG_FILE.with_suffix(".json")


def load_unsent_today() -> list[dict]:
    if not NEWS_LOG_FILE.exists():
        return []
    today_str = date.today().isoformat()
    result = []
    with open(NEWS_LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_found = row.get("date_found", "")
            if date_found.startswith(today_str) and row.get("sent_to_whatsapp", "").strip().lower() == "no":
                row["matched_keywords"] = [kw.strip() for kw in row.get("matched_keywords", "").split(";") if kw.strip()]
                try:
                    row["score"] = int(row.get("score", 0))
                except (ValueError, TypeError):
                    row["score"] = 0
                result.append(row)
    logger.info(f"Loaded {len(result)} unsent articles from today")
    return result


def mark_as_sent(articles: list[dict]):
    if not NEWS_LOG_FILE.exists() or not articles:
        return
    links_to_mark = {a.get("link", "") for a in articles if a.get("link")}
    rows = []
    updated = 0
    with open(NEWS_LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or FIELDNAMES
        for row in reader:
            if row.get("link") in links_to_mark and row.get("sent_to_whatsapp", "").strip().lower() == "no":
                row["sent_to_whatsapp"] = "yes"
                updated += 1
            rows.append(row)
    with open(NEWS_LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Marked {updated} articles as sent in {NEWS_LOG_FILE}")


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
