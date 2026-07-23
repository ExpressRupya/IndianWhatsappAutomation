import logging
from datetime import datetime
from .config import MAX_DIGEST_ITEMS

logger = logging.getLogger(__name__)


def build_article_summary(article: dict) -> str:
    title = article.get("title", "")
    company = article.get("company_matched", "Industry News")
    category = article.get("category", "project")
    source = article.get("source", "")
    snippet = article.get("snippet", "")
    link = article.get("link", "")

    lines = []
    lines.append(f"*{title}*")
    lines.append("")
    lines.append(f"🏢 *Company:* {company}")
    lines.append(f"📂 *Category:* {category.upper()}")
    lines.append(f"📰 *Source:* {source}")
    if snippet:
        safe_snippet = snippet[:250].rsplit(" ", 1)[0] if len(snippet) > 250 else snippet
        lines.append("")
        lines.append(safe_snippet + ("..." if len(snippet) > 250 else ""))
    lines.append("")
    lines.append(f"🔗 {link}")
    lines.append("")
    lines.append(f"📅 {datetime.now().strftime('%d %B %Y')}  |  Express Rupya")
    return "\n".join(lines)


def build_digest(articles: list[dict]) -> str:
    scored = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)

    if not scored:
        return "No relevant data centre news found today."

    land_articles = [a for a in scored if a.get("category") == "land"]
    other_articles = [a for a in scored if a.get("category") != "land"]

    lines = []
    today = datetime.now().strftime('%d %B %Y')
    lines.append(f"*Indian Data Centre News Alert*")
    lines.append(f"_{today}_")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    idx = 1

    lines.append("*LAND ACQUISITION*")
    lines.append("")
    if land_articles:
        for a in land_articles:
            company = a.get("company_matched", "Industry News")
            source = a.get("source", "Unknown")
            snippet = a.get("snippet", "")
            safe = snippet[:120].rsplit(" ", 1)[0] if len(snippet) > 120 else snippet
            lines.append(f"*{idx}.* {a['title']}")
            lines.append(f"   ┣ 🏢 *Company*: {company}")
            lines.append(f"   ┣ 📰 *Source*: {source}")
            if safe:
                lines.append(f"   ┗ {safe}")
            lines.append(f"   🔗 {a['link']}")
            lines.append("")
            idx += 1
    else:
        lines.append("_No land acquisition news today._")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    lines.append("*NEW PROJECTS / EXPANSIONS*")
    lines.append("")
    if other_articles:
        for a in other_articles:
            company = a.get("company_matched", "Industry News")
            source = a.get("source", "Unknown")
            snippet = a.get("snippet", "")
            safe = snippet[:120].rsplit(" ", 1)[0] if len(snippet) > 120 else snippet
            lines.append(f"*{idx}.* {a['title']}")
            lines.append(f"   ┣ 🏢 *Company*: {company}")
            lines.append(f"   ┣ 📰 *Source*: {source}")
            if safe:
                lines.append(f"   ┗ {safe}")
            lines.append(f"   🔗 {a['link']}")
            lines.append("")
            idx += 1
    else:
        lines.append("_No new project announcements today._")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"_{datetime.now().strftime('%d %B %Y')}  ·  Express Rupya_")
    lines.append("_Review for land purchase & new project opportunities._")

    return "\n".join(lines)
