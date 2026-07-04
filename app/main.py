import logging
import os
from datetime import datetime, timedelta, timezone
from .config import MIN_SCORE
from .serpapi_client import fetch_news
from .company_matcher import load_companies, match_company
from .news_scorer import score_article
from .dedupe import filter_duplicates
from .storage import save_articles
from .digest_builder import build_digest
from .whatsapp_sender import send_whatsapp

logger = logging.getLogger(__name__)


def load_queries():
    import pandas as pd
    from .config import QUERIES_FILE
    df = pd.read_csv(QUERIES_FILE)
    return df.to_dict("records")


def _within_24h(article: dict) -> bool:
    raw = article.get("iso_date") or article.get("date", "")
    if not raw:
        return True
    try:
        pub = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - pub <= timedelta(hours=24)
    except (ValueError, TypeError):
        return True


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
    all_articles = [a for a in all_articles if _within_24h(a)]
    logger.info(f"24h filter: {before_filter} -> {len(all_articles)} articles within last 24h")

    before = len(all_articles)
    new_articles = filter_duplicates(all_articles)
    logger.info(f"Duplicates removed: {before} -> {len(new_articles)}")

    above_min = [a for a in new_articles if a.get("score", 0) >= MIN_SCORE]
    scored_articles = [a for a in above_min if a.get("category") in ("land", "project")]
    logger.info(f"Above score threshold ({MIN_SCORE}): {len(above_min)}/{len(new_articles)}")
    logger.info(f"Land/Project only: {len(scored_articles)}/{len(above_min)}")

    if scored_articles:
        save_articles(scored_articles)
    else:
        logger.info("No articles above score threshold to save")

    digest = build_digest(scored_articles)
    logger.info("Digest built")

    send_whatsapp(digest, os.getenv("WHATSAPP_COMMUNITY_NAME", ""))

    return digest
