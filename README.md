# 🏏 RCB Ticket Monitor

> Polls [shop.royalchallengers.com/ticket](https://shop.royalchallengers.com/ticket) every 2 seconds and fires alerts the moment RCB tickets go on sale — macOS notification, phone push, and a voice call.

---

## Features

- **Headless browser polling** — uses Playwright + stealth to render the React SPA and bypass bot detection
- **Multi-channel alerts** — macOS desktop notification, ntfy.sh phone push, Twilio voice call
- **Live dashboard** — FastAPI backend + React UI with start/stop, real-time logs, LED status border, and notification test buttons
- **Re-alerts every 5 minutes** after tickets go live until you stop it

---

## Notifications

| Channel | Service | Cost |
|---|---|---|
| macOS desktop | `terminal-notifier` | Free |
| Phone push | [ntfy.sh](https://ntfy.sh) | Free |
| Voice call | Twilio | ~$0.014/min (free trial credit covers it) |

---

## Requirements

- macOS (tested on macOS 13+)
- Python 3.10+
- Node.js 18+ (for UI build)
- Homebrew

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Satyendra2309/rcb-ticket-notifier.git
cd rcb-ticket-notifier

# Install terminal-notifier
brew install terminal-notifier

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
pip install playwright-stealth
```

### 2. Fix macOS notification permissions

`terminal-notifier` needs explicit permission:

1. Run once from terminal: `terminal-notifier -title "Test" -message "Allow notifications?"`
2. Go to **System Settings → Notifications → terminal-notifier**
3. Toggle **Allow notifications** ON

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in your credentials in `.env` — see the **API Key Setup** section below.

### 4. Build the UI

```bash
cd ui
npm install
npm run build:local
cd ..
```

### 5. Start the server

```bash
source .venv/bin/activate
uvicorn api_server:app --reload
```

Open **[http://localhost:8000/ui](http://localhost:8000/ui)** and click **Start Monitoring**.

---

## API Key Setup

### ntfy.sh — Phone Push Notification (Free, 2 min)

1. Install the **ntfy** app on your phone — [iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
2. Open the app → tap **+** → subscribe to a unique topic name (e.g. `rcb-tickets-yourname123`)
3. Add to `.env`:
   ```
   NTFY_TOPIC=rcb-tickets-yourname123
   ```

> Make the topic name unique — ntfy topics are public by default.

---

### Twilio — Voice Call (~10 min setup)

#### Step 1: Create account
1. Sign up at [twilio.com](https://twilio.com) — free trial gives ~$15 credit
2. Verify your email and phone number

#### Step 2: Get credentials
1. Log into the [Twilio Console](https://console.twilio.com)
2. Copy **Account SID** and **Auth Token** from the Dashboard
3. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token
   ```

#### Step 3: Buy a phone number
1. Console → **Phone Numbers → Manage → Buy a number**
2. Select **United States** (cheapest, ~$1/month), ensure **Voice** is checked → buy
3. Add to `.env`:
   ```
   TWILIO_FROM_NUMBER=+1XXXXXXXXXX
   ```

#### Step 4: Verify your personal number
Trial accounts can only call verified numbers:
1. Console → **Verified Caller IDs → Add a new Caller ID**
2. Enter your number (e.g. `+919876543210`) and verify via OTP
3. Add to `.env`:
   ```
   YOUR_PHONE_NUMBER=+919876543210
   ```

> **E.164 format:** always starts with `+`, then country code. India: `+91XXXXXXXXXX`

---

## Running

### With UI (recommended)

```bash
source .venv/bin/activate
uvicorn api_server:app --reload
# Open http://localhost:8000/ui
```

### CLI only

```bash
source .venv/bin/activate

# Start polling
python poller.py

# Test: simulate tickets going on sale (fires all notifications)
python test_available.py

# Test: simulate tickets unavailable (no notifications)
python test_unavailable.py
```

---

## How it works

The RCB ticket page is a React SPA — a plain HTTP request returns an empty HTML shell. This tool uses **Playwright** to launch a headless Chromium browser, fully execute the JavaScript, and wait until the page content renders. **playwright-stealth** patches the browser fingerprint to bypass Cloudflare bot detection.

Every 2 seconds:
1. Navigate to the page, wait for `networkidle`
2. Wait until `document.body.innerText.length > 50` (confirms React has rendered)
3. Read the full visible body text
4. Check if `"Tickets not available."` is present
5. If it's gone → fire all notifications simultaneously, then re-alert every 5 minutes

---

## Project structure

```
rcb-ticket-notifier/
├── poller.py              # Core polling + notification logic
├── api_server.py          # FastAPI backend (REST API + serves UI)
├── test_available.py      # Test: fires all notifications
├── test_unavailable.py    # Test: no notifications (just logs)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── ui/                    # React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── App.tsx
│   │   └── App.css
│   └── package.json
└── static/ui/             # Built frontend (auto-generated, served at /ui)
```

---

## License

MIT
