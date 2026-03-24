# RCB Ticket Monitor

Polls [shop.royalchallengers.com/ticket](https://shop.royalchallengers.com/ticket) every 2 seconds and fires alerts the moment tickets go on sale.

## Notifications

| Channel | Service | Cost |
|---|---|---|
| macOS desktop | `terminal-notifier` | Free |
| Phone push | ntfy.sh | Free |
| Voice call | Twilio | ~$0.014/min (trial credit covers it) |

## UI

A live dashboard to start/stop monitoring and test all notification channels.

![Dark themed dashboard with start/stop button, stats, and live logs]

---

## Setup

### 1. Prerequisites

```bash
# Python 3.10+
brew install terminal-notifier

# Node 18+ required for UI (check your version)
node --version

# If on Node 16, upgrade via nvm:
nvm install 18 && nvm use 18
```

### 2. Install Python dependencies

```bash
cd rcb-ticket-notifier
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
pip install playwright-stealth
```

### 3. Fix macOS notification permissions

`terminal-notifier` needs permission to show notifications:

1. Run once: `terminal-notifier -title "Test" -message "Allow?"`
2. Go to **System Settings → Notifications → terminal-notifier**
3. Toggle **Allow notifications** ON

### 4. Configure environment

```bash
cp .env.example .env
# Fill in your credentials (see sections below)
```

---

## API Key Setup

### ntfy.sh — Phone Push Notification (Free, 2 min)

1. Install the **ntfy** app on your phone:
   - [iOS App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
2. Open the app → tap **+** → enter a unique topic name (e.g. `rcb-tickets-yourname123`)
3. Set in `.env`:
   ```
   NTFY_TOPIC=rcb-tickets-yourname123
   ```
> Topic names are public — make it unique so strangers don't subscribe to your alerts.

---

### Twilio — Voice Call (~10 min)

#### Step 1: Create account
1. Sign up at [twilio.com](https://twilio.com)
2. Free trial gives ~$15 credit — more than enough

#### Step 2: Get credentials
1. Log into the [Twilio Console](https://console.twilio.com)
2. On the **Dashboard**, copy your **Account SID** and **Auth Token**
3. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token
   ```

#### Step 3: Buy a phone number
1. Console → **Phone Numbers → Manage → Buy a number**
2. Select country **United States** (cheapest, ~$1/month)
3. Ensure **Voice** capability is checked → buy it
4. Add to `.env`:
   ```
   TWILIO_FROM_NUMBER=+1XXXXXXXXXX
   ```

#### Step 4: Verify your personal number
Trial accounts can only call verified numbers:
1. Console → **Verified Caller IDs → Add a new Caller ID**
2. Enter your number in E.164 format (e.g. `+919876543210`)
3. Verify via the OTP call/SMS
4. Add to `.env`:
   ```
   YOUR_PHONE_NUMBER=+919876543210
   ```

> **E.164 format:** `+` → country code → number. India: `+91XXXXXXXXXX`, US: `+1XXXXXXXXXX`

---

## Run (CLI only)

```bash
# Start polling
uv run --with playwright-stealth python poller.py

# Test all notifications fire correctly
uv run --with playwright-stealth python test_available.py

# Test unavailable scenario (no notifications)
uv run --with playwright-stealth python test_unavailable.py
```

---

## Run with UI

### Build the frontend

```bash
cd ui
npm install
npm run build:local
cd ..
```

### Start the server

```bash
uvicorn api_server:app --reload
```

Open [http://localhost:8000/ui](http://localhost:8000/ui)

> For frontend development with hot reload: `cd ui && npm run dev` (proxies API to port 8000)

---

## How it works

The RCB ticket page is a React SPA — a regular HTTP fetch returns an empty shell. We use **Playwright** (headless Chromium) to fully load and execute the page JavaScript, then wait until the DOM has rendered content. **playwright-stealth** patches the browser fingerprint to bypass Cloudflare bot detection.

Every 2 seconds:
1. Navigate to the page, wait for `networkidle`
2. Wait until `document.body.innerText.length > 50` (React has rendered)
3. Read the full body text
4. Check if `"Tickets not available."` is present
5. If missing → fire all notifications, then re-alert every 5 minutes until stopped

---

## Project structure

```
rcb-ticket-notifier/
├── poller.py              # Core polling + notification logic
├── api_server.py          # FastAPI backend
├── test_available.py      # Test: fires all notifications
├── test_unavailable.py    # Test: no notifications
├── requirements.txt
├── .env.example
├── ui/                    # React frontend (Vite + TypeScript)
│   └── src/
│       ├── App.tsx
│       └── App.css
└── static/ui/             # Built frontend (served by FastAPI at /ui)
```
