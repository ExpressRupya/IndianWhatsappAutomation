import logging
from rapidfuzz import fuzz
from .config import NEWS_LOG_FILE

logger = logging.getLogger(__name__)


def load_seen_links() -> set:
    if not NEWS_LOG_FILE.exists():
        return set()
    import pandas as pd
    df = pd.read_csv(NEWS_LOG_FILE)
    seen = set()
    if "link" in df.columns:
        seen = set(df["link"].dropna().str.strip().tolist())
    if "title" in df.columns:
        seen_titles = df["title"].dropna().str.strip().tolist()
    return seen


def is_duplicate(title: str, link: str, seen_titles: list[str], seen_links: set) -> bool:
    link_stripped = link.strip()
    if link_stripped in seen_links:
        return True
    for old_title in seen_titles:
        if fuzz.ratio(title.lower(), old_title.lower()) >= 90:
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
    run_links = set()
    run_titles = []
    for art in articles:
        if not is_duplicate(art["title"], art["link"], seen_titles, seen_links) \
           and art["link"] not in run_links:
            run_links.add(art["link"])
            run_titles.append(art["title"])
            filtered.append(art)
    return filtered
