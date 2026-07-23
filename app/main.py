import logging
import os
import re
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import MIN_SCORE, MAX_ARTICLES, MAX_SEND_MESSAGES
from .serpapi_client import fetch_news
from .company_matcher import load_companies, match_company
from .news_scorer import score_article
from .dedupe import filter_duplicates
from .storage import save_articles, load_unsent_today, mark_as_sent
from .digest_builder import build_digest, build_article_summary
from .whatsapp_sender import send_whatsapp_multi
from .image_gen import generate_article_card, cleanup_temp_images

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


def _published_within_24h(article: dict) -> bool:
    raw = article.get("iso_date") or article.get("date", "")
    if not raw:
        return True
    pub = _parse_article_date(raw)
    if pub is None:
        return True
    from datetime import timezone, timedelta
    if pub.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    return pub >= cutoff


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
            co_name, co_priority = match_company(text, companies)
            scoring = score_article(art["title"], art["snippet"], co_name, co_priority)
            art["company_matched"] = co_name or "Industry News"
            art["company_priority"] = co_priority or ""
            art["score"] = scoring["score"]
            art["matched_keywords"] = scoring["matched_keywords"]
            art["category"] = scoring["category"]
        all_articles.extend(results)

    before_filter = len(all_articles)
    all_articles = [a for a in all_articles if _published_within_24h(a)]
    logger.info(f"24h filter: {before_filter} -> {len(all_articles)} articles within last 24h")

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
        scored_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
        before = len(scored_articles)
        scored_articles = scored_articles[:MAX_ARTICLES]
        if len(scored_articles) < before:
            logger.info(f"Top-{MAX_ARTICLES} selection: {before} -> {len(scored_articles)} articles")
        save_articles(scored_articles)
    else:
        logger.info("No articles above score threshold to save")

    unsent = load_unsent_today()
    all_today = unsent + scored_articles
    seen_links = set()
    all_today_deduped = []
    for a in all_today:
        link = a.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            all_today_deduped.append(a)

    community_name = os.getenv("WHATSAPP_COMMUNITY_NAME", "")

    if all_today_deduped:
        send_limit = MAX_SEND_MESSAGES if MAX_SEND_MESSAGES > 0 else len(all_today_deduped)
        to_send = all_today_deduped[:send_limit]
        logger.info(f"Building individual article cards for {len(to_send)}/{len(all_today_deduped)} articles")

        messages = [None] * len(to_send)

        def build_item(i, article):
            kw = article.get("matched_keywords", [])
            if kw:
                logger.info(f"Article {i} [{article.get('category', '?')}] {article.get('company_matched', '?')}: keywords={kw}")
            summary = build_article_summary(article)
            image_path = generate_article_card(article, i)
            return i, {"text": summary, "image_path": image_path}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(build_item, i, a) for i, a in enumerate(to_send)]
            for future in as_completed(futures):
                i, msg = future.result()
                messages[i] = msg

        messages = [m for m in messages if m]

        digest = build_digest(to_send)
        messages.append({"text": digest, "image_path": ""})

        logger.info(f"Sending {len(messages)} messages ({len(messages)-1} articles + 1 digest)")
        results = send_whatsapp_multi(messages, community_name)

        article_results = results[:-1] if len(results) > 1 else []
        sent_count = sum(1 for r in article_results if r)
        logger.info(f"Sent {sent_count}/{len(article_results)} article messages successfully")

        if any(article_results) and unsent:
            mark_as_sent(unsent)

        cleanup_temp_images()
    else:
        digest = build_digest(all_today_deduped)
        logger.info("No articles to send individually, built empty digest")

    return all_today_deduped
