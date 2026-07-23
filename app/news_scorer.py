import logging
import re

logger = logging.getLogger(__name__)


def _in_text(keyword: str, text: str) -> bool:
    if keyword == "land":
        return bool(re.search(r'\bland\b', text))
    return keyword in text


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
    "investment", "data centre", "data center", "datacenter",
    "colocation", "hyperscaler", "tier iv", "tier 4",
    "edge data", "managed hosting", "captive",
]

NEGATIVE_KEYWORDS = [
    "job", "hiring", "training", "course", "webinar",
    "advertisement", "sponsored", "promoted",
    "cricket", "movie", "entertainment", "bollywood",
]


INDIAN_DC_COMPANIES = [
    "CtrlS", "Nxtra Data", "STT GDC India", "Sify Technologies", "Yotta",
    "Pi Datacentres", "AdaniConneX", "Web Werks", "Net4", "ESDS",
    "NetMagic", "Trimax", "NeevCloud", "Lumina CloudInfra",
    "Digital Connexion", "TATA Communications", "Reliance Communications",
    "Bharti Airtel", "Equinix", "NTT", "Bridge Data Centres",
    "Rackbank", "Zenlayer", "Princeton Digital Group", "CapitaLand",
    "ST Telemedia", "DataGalaxy", "Digital Ocean",
]

PRIORITY_BOOST = {"High": 40, "Medium": 20}


def score_article(title: str, snippet: str, company_name: str | None, priority: str | None = None) -> dict:
    text = f"{title} {snippet}".lower()
    matched_keywords = []
    categories = set()
    score = 0

    for kw in LAND_KEYWORDS:
        if _in_text(kw, text):
            score += 50
            matched_keywords.append(f"[LAND] {kw}")
            categories.add("land")

    for kw in PROJECT_KEYWORDS:
        if _in_text(kw, text):
            score += 40
            matched_keywords.append(f"[PROJECT] {kw}")
            categories.add("project")

    for kw in HIGH_VALUE_KEYWORDS:
        if _in_text(kw, text):
            score += 10
            matched_keywords.append(kw)

    if company_name:
        score += 15
        boost = PRIORITY_BOOST.get(priority, 0)
        score += boost
        if company_name in INDIAN_DC_COMPANIES:
            score += 30
    else:
        score -= 40

    if _in_text("india", text):
        score += 15
    for city in ["hyderabad", "bengaluru", "mumbai", "chennai", "pune", "jaipur", "noida", "gurgaon", "delhi", "kolkata", "thane"]:
        if city in text or city[:-1] in text:
            score += 8

    for kw in NEGATIVE_KEYWORDS:
        if _in_text(kw, text):
            score -= 50

    category = "land" if "land" in categories else "project" if "project" in categories else "general"

    return {
        "score": score,
        "matched_keywords": matched_keywords,
        "category": category,
    }
