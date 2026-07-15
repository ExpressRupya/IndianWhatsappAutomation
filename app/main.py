import logging
import os
import re
from datetime import datetime, date
from .config import MIN_SCORE
from .serpapi_client import fetch_news
from .company_matcher import load_companies, match_company
from .news_scorer import score_article
from .dedupe import filter_duplicates
from .storage import save_articles, load_unsent_today, mark_as_sent
from .digest_builder import build_digest
from .whatsapp_sender import send_whatsapp

logger = logging.getLogger(__name__)


def load_queries():
    import pandas as pd
    from .config import QUERIES_FILE
    df = pd.read_csv(QUERIES_FILE)
    return df.to_dict("records")


# SerpApi's Google News engine usually does NOT populate a clean "iso_date"
# field — the only reliable date is the human string in "date", formatted
# like "07/14/2026, 05:30 PM, +0000 UTC". That isn't valid ISO 8601, so
# datetime.fromisoformat() alone silently fails on almost every article.
_SERPAPI_DATE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4}, \d{1,2}:\d{2} [AP]M, [+-]\d{4})")


def _parse_article_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    match = _SERPAPI_DATE_RE.match(raw)
    if match:
        try:
            return datetime.strptime(match.group(1), "%m/%d/%Y, %I:%M %p, %z")
        except ValueError:
            return None
    return None


def _published_today(article: dict) -> bool:
    raw = article.get("iso_date") or article.get("date", "")
    if not raw:
        return True
    pub = _parse_article_date(raw)
    if pub is None:
        # Couldn't parse it — don't silently drop a possibly-relevant
        # article just because of an unfamiliar date format.
        return True
    return pub.date() == date.today()


def run():
    companies = load_companies()
    queries = load_queries()
    logger.info(f"Loaded {len(companies)} companies and {len(queries)} queries")

    all_articles = []
    for q in queries:
        qname = q["query_name"]
        qtext = q["query"]
        logger.info(f"Fetching query: {qname}")
        results = fetch_news(qtext)
        logger.info(f"  Got {len(results)} results")
        for art in results:
            text = f"{art['title']} {art['snippet']}"
            co = match_company(text, companies)
            scoring = score_article(art["title"], art["snippet"], co)
            art["company_matched"] = co or "Industry News"
            art["score"] = scoring["score"]
            art["matched_keywords"] = scoring["matched_keywords"]
            art["category"] = scoring["category"]
        all_articles.extend(results)

    before_filter = len(all_articles)
    all_articles = [a for a in all_articles if _published_today(a)]
    logger.info(f"Today filter: {before_filter} -> {len(all_articles)} articles published today")

    before = len(all_articles)
    new_articles = filter_duplicates(all_articles)
    logger.info(f"Duplicates removed: {before} -> {len(new_articles)}")

    above_min = [a for a in new_articles if a.get("score", 0) >= MIN_SCORE]
    scored_articles = [a for a in above_min if a.get("category") in ("land", "project")]
    if not scored_articles and above_min:
        scored_articles = above_min
        logger.info(f"No land/project articles — falling back to all {len(scored_articles)} scored articles")
    logger.info(f"Above score threshold ({MIN_SCORE}): {len(above_min)}/{len(new_articles)}")
    logger.info(f"Land/Project only: {len(scored_articles)}/{len(above_min)}")

    if scored_articles:
        save_articles(scored_articles)
    else:
        logger.info("No articles above score threshold to save")

    unsent = load_unsent_today()
    all_today = unsent + scored_articles
    digest = build_digest(all_today)
    logger.info("Digest built")

    community_name = os.getenv("WHATSAPP_COMMUNITY_NAME", "")

    sent_ok = send_whatsapp(digest, community_name)
    if sent_ok and unsent:
        mark_as_sent(unsent)

    return digest
