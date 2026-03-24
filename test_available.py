"""
Test: fires all notification channels.
Simulates 2 unavailable cycles then triggers the alert.

Run: uv run --with playwright-stealth python test_available.py
"""

import time
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from poller import fire_all_notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=== TEST: Simulating tickets going on sale ===")
    for i in range(1, 3):
        logger.info("[%d] Still unavailable. Rechecking in 2s...", i)
        time.sleep(2)
    logger.info("[3] Tickets not available text GONE — firing notifications!")
    fire_all_notifications()
    logger.info("=== Done — check macOS notif, phone push, and call ===")
