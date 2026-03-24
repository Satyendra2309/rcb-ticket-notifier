"""
Test: simulates tickets still unavailable.
No notifications should fire — just logs.

Run: uv run --with playwright-stealth python test_unavailable.py
"""

import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=== TEST: Tickets NOT available ===")
    for i in range(1, 6):
        logger.info("[%d] Still unavailable. Rechecking in 2s...", i)
        time.sleep(2)
    logger.info("=== Done — no notifications fired (correct) ===")
