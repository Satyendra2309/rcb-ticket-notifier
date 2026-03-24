import { useState, useEffect, useRef, useCallback } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface LogEntry {
  ts: string
  level: string
  msg: string
}

interface Status {
  running: boolean
  tickets_available: boolean
  last_checked: string | null
  total_checks: number
  start_time: string | null
  logs: LogEntry[]
}

type TestChannel = 'macos' | 'phone' | 'call'

// ── Helpers ───────────────────────────────────────────────────────────────────

function getUptime(startTime: string | null): string {
  if (!startTime) return '—'
  const diffMs = Date.now() - new Date(startTime).getTime()
  const totalSeconds = Math.floor(diffMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function formatLastChecked(ts: string | null): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleTimeString()
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [status, setStatus] = useState<Status>({
    running: false,
    tickets_available: false,
    last_checked: null,
    total_checks: 0,
    start_time: null,
    logs: [],
  })
  const [loading, setLoading] = useState(false)
  const [uptime, setUptime] = useState('—')
  const [testSuccess, setTestSuccess] = useState<Record<TestChannel, boolean>>({
    macos: false,
    phone: false,
    call: false,
  })

  const logsEndRef = useRef<HTMLDivElement>(null)
  const prevRunningRef = useRef(false)

  // Poll /api/status every second
  useEffect(() => {
    let active = true
    const poll = async () => {
      try {
        const res = await fetch('/api/status')
        if (res.ok && active) {
          const data: Status = await res.json()
          setStatus(data)
        }
      } catch {
        // server unreachable — silently ignore
      }
    }
    poll()
    const id = setInterval(poll, 1000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [])

  // Update uptime every second
  useEffect(() => {
    const id = setInterval(() => {
      setUptime(getUptime(status.start_time))
    }, 1000)
    setUptime(getUptime(status.start_time))
    return () => clearInterval(id)
  }, [status.start_time])

  // Auto-scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [status.logs])

  // Clear loading state once running state changes
  useEffect(() => {
    if (prevRunningRef.current !== status.running) {
      setLoading(false)
      prevRunningRef.current = status.running
    }
  }, [status.running])

  const handleToggle = useCallback(async () => {
    setLoading(true)
    const endpoint = status.running ? '/api/stop' : '/api/start'
    try {
      await fetch(endpoint, { method: 'POST' })
    } catch {
      setLoading(false)
    }
  }, [status.running])

  const handleTest = useCallback(async (channel: TestChannel) => {
    try {
      await fetch(`/api/test/${channel}`, { method: 'POST' })
      setTestSuccess(prev => ({ ...prev, [channel]: true }))
      setTimeout(() => {
        setTestSuccess(prev => ({ ...prev, [channel]: false }))
      }, 2500)
    } catch {
      // ignore
    }
  }, [])

  const alertMode = status.tickets_available

  return (
    <div className={`app${alertMode ? ' alert-mode' : ''}`}>
      {/* ── Alert Banner ── */}
      {alertMode && (
        <div className="alert-banner">
          🎟️ TICKETS AVAILABLE — BUY NOW!
        </div>
      )}

      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <div className="header-logo">
            <span className="logo-icon">🏏</span>
            <div className="header-titles">
              <h1 className="header-title">RCB Ticket Monitor</h1>
              <p className="header-subtitle">Royal Challengers Bangalore · Live Availability Tracker</p>
            </div>
          </div>
          <div className={`status-pill ${status.running ? (alertMode ? 'pill-alert' : 'pill-active') : 'pill-stopped'}`}>
            <span className={`status-dot ${status.running ? (alertMode ? 'dot-alert' : 'dot-active') : 'dot-stopped'}`} />
            {status.running ? (alertMode ? 'TICKETS AVAILABLE!' : 'MONITORING') : 'STOPPED'}
          </div>
        </div>
      </header>

      <main className="main">

        {/* ── Status Card ── */}
        <section className="card status-card">
          <div className="status-card-body">
            <div className="status-text-block">
              <div className={`status-indicator ${status.running ? (alertMode ? 'ind-alert' : 'ind-active') : 'ind-stopped'}`}>
                <span className={`pulse-dot ${status.running ? (alertMode ? 'pulse-alert' : 'pulse-green') : 'pulse-off'}`} />
                <span className="status-label">
                  {status.running
                    ? alertMode
                      ? '🎟️ TICKETS AVAILABLE!'
                      : 'MONITORING ACTIVE'
                    : 'STOPPED'}
                </span>
              </div>
              <p className="status-desc">
                {status.running
                  ? alertMode
                    ? 'Tickets are on sale! All notifications have been fired.'
                    : `Polling every 2s — watching for ticket availability`
                  : 'Start the monitor to watch for ticket availability.'}
              </p>
            </div>

            <button
              className={`toggle-btn${status.running ? ' btn-stop' : ' btn-start'}${loading ? ' btn-loading' : ''}`}
              onClick={handleToggle}
              disabled={loading}
            >
              {loading
                ? status.running
                  ? 'Stopping…'
                  : 'Starting…'
                : status.running
                ? 'Stop Monitoring'
                : 'Start Monitoring'}
            </button>
          </div>
        </section>

        {/* ── Stats Row ── */}
        <section className="card stats-card">
          <div className="stats-row">
            <div className="stat-item">
              <span className="stat-value">{status.total_checks.toLocaleString()}</span>
              <span className="stat-label">Total Checks</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">{formatLastChecked(status.last_checked)}</span>
              <span className="stat-label">Last Checked</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">{status.running ? uptime : '—'}</span>
              <span className="stat-label">Uptime</span>
            </div>
          </div>
        </section>

        <div className="lower-grid">
          {/* ── Test Notifications ── */}
          <section className="card test-card">
            <h2 className="card-title">Test Notifications</h2>
            <p className="card-desc">Fire a test notification to verify each channel is working.</p>
            <div className="test-buttons">
              <button
                className={`test-btn${testSuccess.macos ? ' test-success' : ''}`}
                onClick={() => handleTest('macos')}
              >
                <span className="test-icon">🖥</span>
                <span className="test-label">
                  {testSuccess.macos ? 'Sent!' : 'macOS'}
                </span>
              </button>
              <button
                className={`test-btn${testSuccess.phone ? ' test-success' : ''}`}
                onClick={() => handleTest('phone')}
              >
                <span className="test-icon">📱</span>
                <span className="test-label">
                  {testSuccess.phone ? 'Sent!' : 'Phone'}
                </span>
              </button>
              <button
                className={`test-btn${testSuccess.call ? ' test-success' : ''}`}
                onClick={() => handleTest('call')}
              >
                <span className="test-icon">📞</span>
                <span className="test-label">
                  {testSuccess.call ? 'Calling!' : 'Call'}
                </span>
              </button>
            </div>
          </section>

          {/* ── Live Logs ── */}
          <section className="card logs-card">
            <div className="logs-header">
              <h2 className="card-title">Live Logs</h2>
              <span className="logs-count">{status.logs.length} entries</span>
            </div>
            <div className="logs-body">
              {status.logs.length === 0 ? (
                <div className="logs-empty">No logs yet — start the monitor to see activity.</div>
              ) : (
                status.logs.map((entry, i) => (
                  <div key={i} className={`log-entry log-${entry.level.toLowerCase()}`}>
                    <span className="log-ts">{new Date(entry.ts).toLocaleTimeString()}</span>
                    <span className={`log-level log-badge-${entry.level.toLowerCase()}`}>{entry.level}</span>
                    <span className="log-msg">{entry.msg}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </section>
        </div>

      </main>

      <footer className="footer">
        <p>RCB Ticket Monitor &middot; Checks <a href="https://shop.royalchallengers.com/ticket" target="_blank" rel="noreferrer">shop.royalchallengers.com/ticket</a> every 2 seconds</p>
      </footer>
    </div>
  )
}
