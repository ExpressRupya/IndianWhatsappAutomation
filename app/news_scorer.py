import logging

logger = logging.getLogger(__name__)

LAND_KEYWORDS = [
    "land", "land acquisition", "land purchase", "bought land",
    "acquires land", "land parcel", "acre", "acres",
    "land deal", "land parcel", "land site", "plot",
]

PROJECT_KEYWORDS = [
    "new data centre", "new data center", "announces", "announced",
    "groundbreaking", "breaks ground", "broke ground",
    "begins construction", "to build", "planned",
    "inaugurated", "inaugurates", "launch", "launching",
    "new project", "greenfield", "brownfield", "new campus",
    "new facility", "expansion", "hyperscale campus",
    "opens", "opened", "set up", "sets up", "establish",
    "investment", "investing", "to invest", "commits",
    "data centre park", "data center park", "data centre campus",
]

HIGH_VALUE_KEYWORDS = [
    "funding", "capex", "hyperscale",
    "cloud region", "campus", "substation", "power",
    "renewable", "mw", "capacity", "maharashtra", "mumbai",
    "navi mumbai", "chennai", "hyderabad", "bangalore",
    "bengaluru", "pune", "noida", "policy", "incentive",
    "investment",
]

NEGATIVE_KEYWORDS = [
    "job", "hiring", "training", "course", "webinar",
    "advertisement", "sponsored", "promoted",
]


def score_article(title: str, snippet: str, company_name: str | None) -> dict:
    text = f"{title} {snippet}".lower()
    matched_keywords = []
    categories = set()
    score = 0

    for kw in LAND_KEYWORDS:
        if kw in text:
            score += 50
            matched_keywords.append(f"[LAND] {kw}")
            categories.add("land")

    for kw in PROJECT_KEYWORDS:
        if kw in text:
            score += 40
            matched_keywords.append(f"[PROJECT] {kw}")
            categories.add("project")

    for kw in HIGH_VALUE_KEYWORDS:
        if kw in text:
            score += 10
            matched_keywords.append(kw)

    if company_name:
        score += 10

    if "india" in text:
        score += 10

    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 50

    category = "land" if "land" in categories else "project" if "project" in categories else "general"

    return {
        "score": score,
        "matched_keywords": matched_keywords,
        "category": category,
    }
