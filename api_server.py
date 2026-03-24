"""
RCB Ticket Notifier — FastAPI server
Exposes REST endpoints to start/stop the poller, query status, and test notifications.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os

# ── Logging capture ───────────────────────────────────────────────────────────

MAX_LOG_ENTRIES = 200


class InMemoryLogHandler(logging.Handler):
    """Captures log records into an in-memory deque for the status endpoint."""

    def __init__(self, capacity: int = MAX_LOG_ENTRIES) -> None:
        super().__init__()
        self._records: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": self.format(record),
        }
        with self._lock:
            self._records.append(entry)

    def get_last(self, n: int = 50) -> list:
        with self._lock:
            return list(self._records)[-n:]


_log_handler = InMemoryLogHandler()
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))

# Attach to root logger so all module loggers are captured
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ── Poller state ──────────────────────────────────────────────────────────────

_state_lock = threading.Lock()
_poller_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None

_state: Dict[str, Any] = {
    "running": False,
    "tickets_available": False,
    "last_checked": None,
    "total_checks": 0,
    "start_time": None,
}


def _state_callback(update: Dict[str, Any]) -> None:
    with _state_lock:
        _state["tickets_available"] = update.get("tickets_available", False)
        _state["last_checked"] = datetime.now(tz=timezone.utc).isoformat()
        _state["total_checks"] = update.get("attempt", _state["total_checks"])


def _run_poller_thread(stop_event: threading.Event) -> None:
    try:
        from poller import run_poller
        run_poller(stop_event=stop_event, state_callback=_state_callback)
    except Exception as exc:
        logger.error("Poller thread crashed: %s", exc)
    finally:
        with _state_lock:
            _state["running"] = False
        logger.info("Poller thread exited")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="RCB Ticket Notifier", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static UI only if the directory exists
_ui_dir = os.path.join(os.path.dirname(__file__), "static", "ui")
if os.path.isdir(_ui_dir):
    app.mount("/ui", StaticFiles(directory=_ui_dir, html=True), name="ui")
else:
    logger.warning("static/ui directory not found — UI not mounted. Run `npm run build:local` inside ui/")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status() -> JSONResponse:
    with _state_lock:
        snapshot = dict(_state)
    snapshot["logs"] = _log_handler.get_last(50)
    return JSONResponse(snapshot)


@app.post("/api/start")
def start_poller() -> JSONResponse:
    global _poller_thread, _stop_event

    with _state_lock:
        if _state["running"]:
            return JSONResponse({"ok": False, "message": "Poller already running"}, status_code=409)

    _stop_event = threading.Event()
    _poller_thread = threading.Thread(target=_run_poller_thread, args=(_stop_event,), daemon=True)

    with _state_lock:
        _state["running"] = True
        _state["tickets_available"] = False
        _state["total_checks"] = 0
        _state["start_time"] = datetime.now(tz=timezone.utc).isoformat()
        _state["last_checked"] = None

    _poller_thread.start()
    logger.info("Poller started via API")
    return JSONResponse({"ok": True, "message": "Poller started"})


@app.post("/api/stop")
def stop_poller() -> JSONResponse:
    global _poller_thread, _stop_event

    with _state_lock:
        running = _state["running"]

    if not running:
        return JSONResponse({"ok": False, "message": "Poller is not running"}, status_code=409)

    if _stop_event:
        _stop_event.set()

    logger.info("Stop signal sent to poller via API")
    return JSONResponse({"ok": True, "message": "Stop signal sent"})


@app.post("/api/test/macos")
def test_macos() -> JSONResponse:
    try:
        from poller import notify_macos
        notify_macos("RCB Test", "macOS notification test from RCB Ticket Monitor")
        return JSONResponse({"ok": True, "message": "macOS notification triggered"})
    except Exception as exc:
        logger.error("macOS test failed: %s", exc)
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


@app.post("/api/test/phone")
def test_phone() -> JSONResponse:
    try:
        from poller import notify_ntfy
        notify_ntfy("RCB Test", "Phone notification test from RCB Ticket Monitor")
        return JSONResponse({"ok": True, "message": "Phone notification triggered"})
    except Exception as exc:
        logger.error("Phone test failed: %s", exc)
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


@app.post("/api/test/call")
def test_call() -> JSONResponse:
    try:
        from poller import notify_call
        notify_call("This is a test call from the R C B Ticket Monitor.")
        return JSONResponse({"ok": True, "message": "Call triggered"})
    except Exception as exc:
        logger.error("Call test failed: %s", exc)
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
