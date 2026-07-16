import logging
import re
from rapidfuzz import fuzz
from .config import NEWS_LOG_FILE

logger = logging.getLogger(__name__)

SAME_RUN_THRESHOLD = 72
HISTORY_THRESHOLD = 88


def _normalize(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    tokens = [t for t in title.split() if t not in {"a", "an", "the", "in", "of", "to", "for", "at", "on", "by", "is", "and", "with", "its", "as"}]
    return " ".join(tokens)


def _key_terms(title: str) -> set:
    title = title.lower()
    terms = set()
    for m in re.finditer(r"\b(aws|amazon|google|microsoft|equinix|ntt|sify|ctrl[ms]|adani|reliance|tata|airtrunk|submer|hcltech|hcl|capitalland|esds|net4|pi[- ]?datacentres?|stt|nxtra|yotta|bharti|jio|reliane|google cloud|oracle|ibm)\b", title):
        terms.add(m.group(1))
    for m in re.finditer(r"\b(hyderabad|bengaluru|mumbai|delhi|chennai|pune|jaipur|gujarat|karnataka|telangana|andhra|madhya|tamil nadu|india)\b", title):
        terms.add(m.group(1))
    for m in re.finditer(r"\b(\d[\d,]*\s*(crore|lakh|billion|mn|bn|mw|gw|acre|acres))\b", title.lower()):
        terms.add(m.group(0))
    for m in re.finditer(r"\b(breaks ground|foundation|inaugurat|launch|expand|invest|new data[-\s]?centre?|ai[- ]?ready|hyperscale|renewable|solar|campus)\b", title):
        terms.add(m.group(1))
    return terms


def _title_similarity(t1: str, t2: str) -> float:
    nt1 = _normalize(t1)
    nt2 = _normalize(t2)
    if not nt1 or not nt2:
        return 0.0
    ratio = fuzz.ratio(nt1, nt2)
    partial = fuzz.partial_ratio(nt1, nt2)
    token_sort = fuzz.token_sort_ratio(nt1, nt2)
    token_set = fuzz.token_set_ratio(nt1, nt2)
    terms1 = _key_terms(t1)
    terms2 = _key_terms(t2)
    overlap = len(terms1 & terms2)
    total = len(terms1 | terms2)
    term_score = (overlap / total * 100) if total > 0 else 0
    return max(ratio, partial, token_sort, token_set, term_score)


def load_seen_links() -> set:
    if not NEWS_LOG_FILE.exists():
        return set()
    import pandas as pd
    df = pd.read_csv(NEWS_LOG_FILE)
    seen = set()
    if "link" in df.columns:
        seen = set(df["link"].dropna().str.strip().tolist())
    return seen


def is_duplicate(title: str, link: str, seen_titles: list[str], seen_links: set) -> bool:
    link_stripped = link.strip()
    if link_stripped in seen_links:
        return True
    for old_title in seen_titles:
        if _title_similarity(title, old_title) >= HISTORY_THRESHOLD:
            return True
    return False


def filter_duplicates(articles: list[dict]) -> list[dict]:
    seen_links = load_seen_links()
    import pandas as pd
    if NEWS_LOG_FILE.exists():
        df = pd.read_csv(NEWS_LOG_FILE)
        seen_titles = df["title"].dropna().str.strip().tolist() if "title" in df.columns else []
    else:
        seen_titles = []

    filtered = []
    run_seen_links = set()
    run_seen_titles = []

    for art in sorted(articles, key=lambda x: x.get("score", 0), reverse=True):
        title = art["title"]
        link = art["link"]

        if link in run_seen_links:
            logger.debug(f"Duplicate link (same run): {title[:60]}")
            continue

        if is_duplicate(title, link, seen_titles, seen_links):
            logger.debug(f"Duplicate vs history: {title[:60]}")
            continue

        dup = False
        for existing_title in run_seen_titles:
            if _title_similarity(title, existing_title) >= SAME_RUN_THRESHOLD:
                logger.info(f"Duplicate story (same run): {title[:60]} ~~ {existing_title[:60]}")
                dup = True
                break

        if dup:
            continue

        run_seen_links.add(link)
        run_seen_titles.append(title)
        filtered.append(art)

    removed = len(articles) - len(filtered)
    if removed:
        logger.info(f"Within-run dedup removed {removed} duplicate articles")
    return filtered
