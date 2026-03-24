"""
RCB Ticket Poller
Polls https://shop.royalchallengers.com/ticket every 2 seconds.
Fires macOS notification, phone push, and a voice call the moment
"Tickets not available." disappears. Re-alerts every 5 mins until Ctrl+C.
"""

import subprocess
import time
import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

TARGET_URL = "https://shop.royalchallengers.com/ticket"
UNAVAILABLE_TEXT = "Tickets not available."
POLL_INTERVAL_SECONDS = 2
RECHECK_INTERVAL_SECONDS = 5 * 60

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
YOUR_PHONE_NUMBER = os.environ.get("YOUR_PHONE_NUMBER", "")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ── Notifications ─────────────────────────────────────────────────────────────

def notify_macos(title: str, message: str) -> None:
    result = subprocess.run(
        ["terminal-notifier", "-title", title, "-message", message, "-sound", "Glass"],
        capture_output=True,
    )
    if result.returncode == 0:
        logger.info("macOS notification sent")
    else:
        logger.error("macOS notification failed: %s", result.stderr.decode())


def notify_ntfy(title: str, message: str) -> None:
    if not NTFY_TOPIC:
        logger.warning("NTFY_TOPIC not set — skipping phone notification")
        return
    try:
        import requests
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "urgent", "Tags": "ticket,rotating_light"},
            timeout=10,
        ).raise_for_status()
        logger.info("Phone notification sent")
    except Exception as e:
        logger.error("Phone notification failed: %s", e)


def notify_call(message: str) -> None:
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, YOUR_PHONE_NUMBER]):
        logger.warning("Twilio env vars not set — skipping call")
        return
    try:
        from twilio.rest import Client
        from twilio.twiml.voice_response import VoiceResponse
        twiml = VoiceResponse()
        twiml.say(message, voice="Polly.Joanna-Generative", language="en-US")
        twiml.pause(length=1)
        twiml.say(message, voice="Polly.Joanna-Generative", language="en-US")
        call = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).calls.create(
            to=YOUR_PHONE_NUMBER,
            from_=TWILIO_FROM_NUMBER,
            twiml=str(twiml),
        )
        logger.info("Call initiated — SID: %s", call.sid)
    except Exception as e:
        logger.error("Call failed: %s", e)


def fire_all_notifications() -> None:
    title = "RCB TICKETS AVAILABLE!"
    message = "RCB tickets are NOW on sale! Go buy: https://shop.royalchallengers.com/ticket"
    call_message = (
        "Alert! R C B tickets are now available. "
        "Go to shop dot royalchallengers dot com slash ticket to buy now. Hurry!"
    )
    notify_macos(title, message)
    notify_ntfy(title, message)
    notify_call(call_message)


# ── Poller ────────────────────────────────────────────────────────────────────

def fetch_page_text(page) -> str:
    """Fetch the page and return rendered body text. Returns empty string on failure."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    try:
        logger.debug("Navigating to %s", TARGET_URL)
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60_000)
        logger.debug("networkidle reached — waiting for React to render...")
        page.wait_for_function(
            "() => document.body.innerText.trim().length > 50",
            timeout=15_000
        )
        text = page.inner_text("body")
        logger.debug("Fetched content: %s", text.replace("\n", " | ")[:300])
        return text
    except PlaywrightTimeoutError:
        logger.warning("Page timed out — will retry")
        return ""
    except Exception as e:
        logger.warning("Error fetching page: %s", e)
        return ""


def run_poller(stop_event=None, state_callback=None) -> None:
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        logger.error("Run: uv run --with playwright-stealth python poller.py")
        sys.exit(1)

    logger.info("Starting RCB ticket poller — checking every %ds", POLL_INTERVAL_SECONDS)
    logger.info("Target: %s", TARGET_URL)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        Stealth().apply_stealth_sync(context)
        page = context.new_page()


        attempt = 0
        tickets_available = False

        while True:
            if stop_event and stop_event.is_set():
                logger.info("Stop event received — shutting down poller")
                break

            attempt += 1
            body_text = fetch_page_text(page)

            if not body_text.strip():
                logger.warning("[%d] Empty body — site may be down or blocking. Retrying in %ds...", attempt, POLL_INTERVAL_SECONDS)
                if state_callback:
                    state_callback({"attempt": attempt, "tickets_available": tickets_available})
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            logger.info("[%d] Fetched %d chars | Unavailable: %s", attempt, len(body_text), UNAVAILABLE_TEXT in body_text)

            if UNAVAILABLE_TEXT in body_text:
                if tickets_available:
                    logger.info("Tickets went back to unavailable — resuming normal polling")
                    tickets_available = False
                if state_callback:
                    state_callback({"attempt": attempt, "tickets_available": False})
                time.sleep(POLL_INTERVAL_SECONDS)
            else:
                tickets_available = True
                logger.info("[%d] TICKETS AVAILABLE — firing all notifications!", attempt)
                if state_callback:
                    state_callback({"attempt": attempt, "tickets_available": True})
                fire_all_notifications()
                logger.info("Re-alerting every %d mins — press Ctrl+C to stop", RECHECK_INTERVAL_SECONDS // 60)
                # Sleep in small increments so stop_event is checked
                elapsed = 0
                while elapsed < RECHECK_INTERVAL_SECONDS:
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(min(1, RECHECK_INTERVAL_SECONDS - elapsed))
                    elapsed += 1


if __name__ == "__main__":
    run_poller()
