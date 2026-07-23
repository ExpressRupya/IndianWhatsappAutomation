import re
import logging
import pandas as pd
from rapidfuzz import fuzz
from .config import COMPANIES_FILE

logger = logging.getLogger(__name__)

DC_CONTEXT_KEYWORDS = [
    "data centre", "data center", "datacenter",
    "land", "acre", "acres",
    "campus", "facility", "expansion",
    "hyperscale", "hyperscaler", "cloud",
    "power", "substation", "renewable", "green energy",
    "colocation", "investment", "capex",
    "mw", "megawatt", "capacity",
    "groundbreaking", "ground breaking", "inaugurat",
    "construction", "greenfield", "brownfield",
    "server", "edge data", "tier",
    "data centre park", "data center park",
]


def _has_dc_context(text: str) -> bool:
    t = text.lower()
    for kw in DC_CONTEXT_KEYWORDS:
        if kw in t:
            return True
    return False


def load_companies() -> list[dict]:
    df = pd.read_csv(COMPANIES_FILE)
    companies = []
    for _, row in df.iterrows():
        name = str(row["company_name"]).strip()
        aliases = str(row.get("aliases", "")).strip()
        alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases else []
        companies.append({
            "name": name,
            "aliases": alias_list + [name],
            "priority": str(row.get("priority", "Medium")).strip(),
            "status": str(row.get("status", "Active")).strip(),
        })
    return companies


def match_company(text: str, companies: list[dict]) -> tuple:
    if not _has_dc_context(text):
        return (None, None)
    text_lower = text.lower()
    for co in companies:
        if co["status"].lower() != "active":
            continue
        for alias in co["aliases"]:
            alias_lower = alias.lower()
            if alias_lower in text_lower:
                return (co["name"], co.get("priority", "Medium"))
            if fuzz.partial_ratio(alias_lower, text_lower) >= 85:
                return (co["name"], co.get("priority", "Medium"))
    return (None, None)
