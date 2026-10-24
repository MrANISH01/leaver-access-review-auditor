import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Info, RefreshCw, XCircle } from 'lucide-react'
import { api } from '../services/api.js'
import { API_BASE_URL, DATA_MODE, IS_DEMO, MOCK_SCENARIO } from '../services/config.js'
import { mockAdapter } from '../services/mockAdapter.js'
import { liveAdapter } from '../services/liveAdapter.js'
import { executionPersistenceMode, loadExecutionState } from '../services/executionStore.js'
import { loadState, persistenceMode } from '../services/requestStore.js'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import { formatDateTime } from '../utils/format.js'

const REQUIRED_METHODS = [
  'getOverview', 'getFindings', 'getRequests', 'createRequest', 'decideRequest',
  'getExecutionData', 'executeRequest', 'verifyExecution', 'getAuditTrail', 'resetDemoRequests',
]

const STATUS = {
  ok: { icon: CheckCircle2, tone: 'success', label: 'Checked: OK' },
  fail: { icon: XCircle, tone: 'danger', label: 'Checked: problem' },
  unverified: { icon: Info, tone: 'warning', label: 'Not verified' },
}

// Only checks that run inside this browser are marked as checked. Nothing here contacts a backend.
function runChecks() {
  const checks = []

  let storageOk = false
  let storageDetail = ''
  try {
    const key = 'leaverguard.statuscheck'
    window.localStorage.setItem(key, '1')
    storageOk = window.localStorage.getItem(key) === '1'
    window.localStorage.removeItem(key)
    storageDetail = storageOk ? 'A test value was written, read back and removed.' : 'A test value could not be read back.'
  } catch (caught) {
    storageDetail = `Browser storage is blocked (${caught?.name || 'error'}). Demo records last only until the page is reloaded.`
  }
  checks.push({ id: 'storage', name: 'Browser localStorage', state: storageOk ? 'ok' : 'fail', detail: storageDetail })

  const adapter = IS_DEMO ? mockAdapter : liveAdapter
  const missing = REQUIRED_METHODS.filter((name) => typeof adapter[name] !== 'function')
  checks.push({
    id: 'methods', name: 'API adapter methods',
    state: missing.length === 0 && api === adapter ? 'ok' : 'fail',
    detail: missing.length === 0
      ? `All ${REQUIRED_METHODS.length} methods the pages use are defined on the ${IS_DEMO ? 'mock' : 'live'} adapter. This checks the code, not a network connection.`
      : `Missing methods: ${missing.join(', ')}.`,
  })

  if (IS_DEMO) {
    try {
      const { requests, events } = loadState()
      checks.push({
        id: 'requests', name: 'Demo request store', state: 'ok',
        detail: `Readable. ${requests.length} requests and ${events.length} recorded events (${persistenceMode() === 'browser' ? 'saved in this browser' : 'memory only'}).`,
      })
    } catch {
      checks.push({ id: 'requests', name: 'Demo request store', state: 'fail', detail: 'The saved request data could not be read.' })
    }
    try {
      const { executions, verifications } = loadExecutionState()
      checks.push({
        id: 'executions', name: 'Demo execution store', state: 'ok',
        detail: `Readable. ${executions.length} executions and ${verifications.length} verifications (${executionPersistenceMode() === 'browser' ? 'saved in this browser' : 'memory only'}).`,
      })
    } catch {
      checks.push({ id: 'executions', name: 'Demo execution store', state: 'fail', detail: 'The saved execution data could not be read.' })
    }
  }

  checks.push({
    id: 'backend', name: 'Backend API',
    state: 'unverified',
    detail: IS_DEMO
      ? 'Not used in demo mode. No backend is contacted and none is claimed to be connected.'
      : `Configured address: ${API_BASE_URL}. The live adapter is not implemented yet and no health check has been run, so connection is unverified.`,
  })
  return checks
}

const INTEGRATIONS = [
  ['Identity and HR source systems', 'Not connected. Findings come from the built-in synthetic dataset.'],
  ['Account disable or removal in real systems', 'Not available. Execution is simulated and never changes a real account.'],
  ['Real sign-in and authorization', 'Not available. Analyst and approver are demo labels chosen in the top bar.'],
]

export default function SystemStatus() {
  const [result, setResult] = useState(() => ({ checks: runChecks(), checkedAt: new Date().toISOString() }))
  const refresh = useCallback(() => setResult({ checks: runChecks(), checkedAt: new Date().toISOString() }), [])
  useEffect(() => { document.title = 'System status · LeaverGuard' }, [])

  return (
    <>
      <PageHeader
        title="System status"
        description="What this app is configured to use and what could actually be checked from the browser."
        actions={<button type="button" className="btn btn--secondary" onClick={refresh}><RefreshCw size={16} aria-hidden="true" /> Refresh status</button>}
      />

      <div className={`callout ${IS_DEMO ? 'tone-warning' : 'tone-brand'}`} role="note">
        <Info size={18} aria-hidden="true" />
        <p>
          {IS_DEMO
            ? 'Demo mode: all data is synthetic and stored in this browser. No backend, real account or external system is involved.'
            : 'Live mode is selected, but the live API adapter is not built yet. No backend connection has been made or verified.'}
        </p>
      </div>

      <div className="status-grid" style={{ marginTop: 16 }}>
        <Card title="Configuration" subtitle="Read from the app's settings, not tested.">
          <dl className="kv">
            <dt>Application mode</dt><dd>{DATA_MODE === 'live' ? 'Live' : 'Demo (mock)'}</dd>
            <dt>API adapter</dt><dd>{IS_DEMO ? 'Mock adapter (built-in data)' : 'Live adapter (not implemented yet)'}</dd>
            <dt>Backend address</dt><dd>{IS_DEMO ? 'Not used in demo mode' : <code className="code-chip">{API_BASE_URL}</code>}</dd>
            {IS_DEMO && (<><dt>Demo scenario</dt><dd>{MOCK_SCENARIO}</dd></>)}
            <dt>Last status check</dt><dd><time dateTime={result.checkedAt}>{formatDateTime(result.checkedAt)}</time></dd>
          </dl>
          <p className="status-meta">Set in <code className="code-chip">.env.local</code>. Restart the dev server after changing it.</p>
        </Card>

        <Card title="Checks" subtitle="“Checked” means the test ran in this browser just now.">
          <ul className="check-list">
            {result.checks.map((check) => {
              const status = STATUS[check.state]
              const Icon = status.icon
              return (
                <li key={check.id}>
                  <span className={`pill tone-${status.tone}`}><Icon size={13} aria-hidden="true" /> {status.label}</span>
                  <div className="check-list__body"><strong>{check.name}</strong><span>{check.detail}</span></div>
                </li>
              )
            })}
          </ul>
        </Card>
      </div>

      <div style={{ marginTop: 16 }}>
        <Card title="Unavailable integrations" subtitle="Not part of this demo build.">
          <ul className="check-list">
            {INTEGRATIONS.map(([name, text]) => (
              <li key={name}>
                <span className="pill tone-neutral">Unavailable</span>
                <div className="check-list__body"><strong>{name}</strong><span>{text}</span></div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
