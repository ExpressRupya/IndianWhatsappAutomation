import subprocess
import json
import logging
import os
from pathlib import Path
from .config import BASE_DIR

logger = logging.getLogger(__name__)

NODE_SCRIPT = BASE_DIR / "send_to_community.js"
SESSION_DIR = BASE_DIR / ".wwebjs_auth" / "session-dc_news_bot"


def _clean_stale_locks():
    locked_files = [
        SESSION_DIR / "SingletonLock",
        SESSION_DIR / "SingletonSocket",
        SESSION_DIR / "first_party_sets.db-journal",
    ]
    for f in locked_files:
        try:
            if f.exists():
                f.unlink()
                logger.debug(f"Removed stale lock: {f.name}")
        except Exception:
            pass


def send_whatsapp(digest: str, community_name: str = "") -> bool:
    _clean_stale_locks()

    if not community_name:
        community_name = os.getenv("WHATSAPP_COMMUNITY_NAME", "")

    if not community_name:
        logger.warning("WHATSAPP_COMMUNITY_NAME not set — skipping WhatsApp")
        return False

    if not NODE_SCRIPT.exists():
        logger.error(f"send_to_community.js not found at {NODE_SCRIPT}")
        return False

    payload = json.dumps({
        "community_name": community_name,
        "message": digest,
    })

    try:
        result = subprocess.run(
            ["node", str(NODE_SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120000,
            cwd=str(BASE_DIR),
        )
        output = result.stdout.strip()
        if output:
            logger.info(f"Node.js output: {output}")

        if "MESSAGE_SENT" in output:
            logger.info("WhatsApp message sent successfully")
            return True
        elif "QR_CODE_REQUIRED" in output:
            logger.warning("QR code needed — run 'node setup_whatsapp.js' in automation/ folder once to authenticate")
            return False
        elif "QR_TIMEOUT" in output:
            logger.warning("QR scan timed out — run 'node setup_whatsapp.js' to authenticate")
            return False
        elif "COMMUNITY_NOT_FOUND" in output:
            logger.error(f"Community '{community_name}' not found in WhatsApp chats")
            return False
        elif "AUTH_FAILURE" in output:
            logger.error(f"WhatsApp auth failure: {output}")
            return False
        elif result.stderr and "Error" in result.stderr:
            logger.error(f"Node.js error: {result.stderr}")
            return False
        else:
            if not output:
                logger.warning("Node.js produced no output (may need first-time Chromium setup)")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Node.js script timed out (2 min)")
        return False
    except FileNotFoundError:
        logger.error("Node.js not found — is it installed and on PATH?")
        return False
