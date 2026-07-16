#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import LOG_FILE
from app.main import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Indian Data Centre News Automation")
    try:
        articles = run()
        if articles:
            land_count = sum(1 for a in articles if a.get("category") == "land")
            project_count = sum(1 for a in articles if a.get("category") == "project")
            out = f"\nSent {len(articles)} articles ({land_count} land, {project_count} project)\n"
            for a in articles:
                title = a['title'][:80].encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
                out += f"  - {a.get('company_matched', 'Industry News')}: {title}\n"
            print(out)
        else:
            print("\nNo relevant data centre news found today.")
        logger.info("Automation completed successfully")
    except Exception as e:
        logger.exception(f"Automation failed: {e}")
        sys.exit(1)
