import logging
from datetime import datetime
from .config import MAX_DIGEST_ITEMS

logger = logging.getLogger(__name__)


def build_digest(articles: list[dict]) -> str:
    scored = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)
    top = scored[:MAX_DIGEST_ITEMS]

    if not top:
        return "No relevant data centre news found today."

    land_articles = [a for a in top if a.get("category") == "land"]
    project_articles = [a for a in top if a.get("category") == "project"]

    lines = []
    lines.append("Indian Data Centre News Alert")
    lines.append(f"Date: {datetime.now().strftime('%d %B %Y')}")
    lines.append("")

    def fmt_article(art, idx):
        company = art.get("company_matched", "Industry News")
        source = art.get("source", "Unknown")
        kw = "; ".join(art.get("matched_keywords", []))
        lines.append(f"{idx}. {art['title']}")
        lines.append(f"   Company: {company}")
        lines.append(f"   Source: {source}")
        lines.append(f"   Keywords: {kw}")
        lines.append(f"   Link: {art['link']}")
        lines.append("")

    idx = 1

    lines.append("LAND ACQUISITION")
    lines.append("-" * 40)
    if land_articles:
        for a in land_articles:
            fmt_article(a, idx)
            idx += 1
    else:
        lines.append("  No land acquisition news today.")
        lines.append("")
    lines.append("")

    lines.append("NEW PROJECTS / EXPANSIONS")
    lines.append("-" * 40)
    if project_articles:
        for a in project_articles:
            fmt_article(a, idx)
            idx += 1
    else:
        lines.append("  No new project announcements today.")
        lines.append("")
    lines.append("")

    lines.append("-" * 40)
    lines.append("Express Rupya: Review for land purchase & new project opportunities.")

    return "\n".join(lines)
