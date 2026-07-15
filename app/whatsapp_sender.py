import subprocess
import json
import logging
import os
import time
import re
from pathlib import Path
from .config import BASE_DIR

logger = logging.getLogger(__name__)

NODE_SCRIPT = BASE_DIR / "send_to_community.js"
SESSION_DIR = BASE_DIR / ".wwebjs_auth" / "session-dc_news_bot"

_RESULT_RE = re.compile(r"^RESULT:")


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


def _parse_result(output: str) -> dict | None:
    for line in output.splitlines():
        if _RESULT_RE.match(line):
            try:
                return json.loads(line[len("RESULT:"):])
            except json.JSONDecodeError:
                return None
    return None


def _run_node(payload: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(NODE_SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=150,
        cwd=str(BASE_DIR),
    )


def send_whatsapp(digest: str, community_name: str = "") -> bool:
    _clean_stale_locks()

    if not community_name:
        community_name = os.getenv("WHATSAPP_COMMUNITY_NAME", "")

    target_chat_id = os.getenv("WHATSAPP_TARGET_CHAT_ID", "")

    if not community_name and not target_chat_id:
        logger.warning("Neither WHATSAPP_COMMUNITY_NAME nor WHATSAPP_TARGET_CHAT_ID set — skipping WhatsApp")
        return False

    if not NODE_SCRIPT.exists():
        logger.error(f"send_to_community.js not found at {NODE_SCRIPT}")
        return False

    payload = json.dumps({
        "community_name": community_name,
        "chat_id": target_chat_id,
        "message": digest,
    })

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            result = _run_node(payload)
            output = (result.stdout or "").strip()
            if output:
                for line in output.splitlines():
                    if not line.startswith("RETRY_LOG"):
                        logger.info(f"Node.js output: {line}")

            parsed = _parse_result(output)

            if parsed is None:
                # Legacy / fallback status strings
                if "MESSAGE_SENT" in output:
                    logger.warning("Legacy MESSAGE_SENT marker found without JSON result — treating as best-effort success")
                    return True
                elif "QR_CODE_REQUIRED" in output:
                    logger.warning("QR code needed — run 'node setup_whatsapp.js' once to authenticate")
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
                elif "SEND_ERROR" in output:
                    err_line = next((line for line in output.splitlines() if "SEND_ERROR" in line), output)
                    logger.error(f"WhatsApp send error: {err_line}")
                    return False
                else:
                    if not output:
                        logger.warning("Node.js produced no output")
                    return False

            status = parsed.get("status")

            if status == "sent":
                sent_chat_id = parsed.get("chat_id", "")
                msg_id = parsed.get("message_id", "")
                ack = parsed.get("ack", -1)
                chat_name = parsed.get("chat_name", "unknown")

                logger.info(
                    f"Message confirmed sent to '{chat_name}' "
                    f"(chat_id={sent_chat_id}, msg_id={msg_id}, ack={ack})"
                )

                if ack < 0 and msg_id:
                    logger.warning(f"Message has no ack ({ack}) — may not have reached server")
                    return False

                if target_chat_id and sent_chat_id != target_chat_id:
                    logger.error(
                        f"Message sent to wrong chat! expected={target_chat_id}, actual={sent_chat_id}"
                    )
                    return False

                return True

            elif status == "not_found":
                logger.error(f"Target not found: {parsed.get('error', '')}")
                return False

            elif status == "error":
                err_msg = parsed.get("error", "Unknown error")
                if attempt < max_attempts:
                    logger.warning(f"Transient error (attempt {attempt}/{max_attempts}) — retrying in 3s: {err_msg}")
                    time.sleep(3)
                    continue
                logger.error(f"WhatsApp send error: {err_msg}")
                return False

            else:
                logger.error(f"Unknown result status: {parsed}")
                return False

        except subprocess.TimeoutExpired:
            if attempt < max_attempts:
                logger.warning(f"Timeout (attempt {attempt}/{max_attempts}) — retrying in 3s")
                time.sleep(3)
                continue
            logger.error("Node.js script timed out")
            return False
        except FileNotFoundError:
            logger.error("Node.js not found — is it installed and on PATH?")
            return False

    return False
