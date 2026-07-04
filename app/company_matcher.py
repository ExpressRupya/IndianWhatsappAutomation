import re
import logging
import pandas as pd
from rapidfuzz import fuzz
from .config import COMPANIES_FILE

logger = logging.getLogger(__name__)


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


def match_company(text: str, companies: list[dict]) -> str | None:
    text_lower = text.lower()
    for co in companies:
        if co["status"].lower() != "active":
            continue
        for alias in co["aliases"]:
            alias_lower = alias.lower()
            if alias_lower in text_lower:
                return co["name"]
            if fuzz.partial_ratio(alias_lower, text_lower) >= 85:
                return co["name"]
    return None
