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
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Indian Data Centre News Automation")
    try:
        digest = run()
        print("\n" + digest + "\n")
        logger.info("Automation completed successfully")
    except Exception as e:
        logger.exception(f"Automation failed: {e}")
        sys.exit(1)
