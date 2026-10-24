import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, ClipboardCheck, Play, RefreshCw, Search, SearchX, ShieldCheck, X } from 'lucide-react'
import { api } from '../services/api.js'
import { IS_DEMO } from '../services/config.js'
import useAsync from '../hooks/useAsync.js'
import { useDemoRole } from '../context/DemoRole.jsx'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import Drawer from '../components/Drawer.jsx'
import ExecutionDetail from '../components/ExecutionDetail.jsx'
import ExecutionTable from '../components/ExecutionTable.jsx'
import { EmptyState, ErrorState } from '../components/States.jsx'

const FILTER_OPTIONS = [
  { key: '', label: 'All' },
  { key: 'pending', label: 'Needs execution' },
  { key: 'executed', label: 'Executed' },
  { key: 'verified', label: 'Verified' },
  { key: 'unverified', label: 'Needs verification' },
]

function matches(request, needle) {
  const snapshot = request.snapshot ?? {}
  const haystack = [
    request.id, request.requestedBy,
    snapshot.employeeName, snapshot.employeeId, snapshot.system, snapshot.accountId,
  ].filter(Boolean).join(' ').toLowerCase()
  return haystack.includes(needle)
}

export default function Execution() {
  const { data, loading, error, reload } = useAsync(api.getExecutionData)
  const { role } = useDemoRole()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState(null)

  const filterParam = params.get('filter') ?? ''
  const filter = FILTER_OPTIONS.some((f) => f.key === filterParam) ? filterParam : ''
  const selectedId = params.get('request') ?? ''

  function update(changes) {
    setParams((previous) => {
      const next = new URLSearchParams(previous)
      for (const [key, value] of Object.entries(changes)) {
        if (value === '' || value === null || value === undefined) next.delete(key)
        else next.set(key, String(value))
      }
      return next
    }, { replace: true })
  }

  const requests = data?.requests ?? []
  const executions = data?.executions ?? []
  const verifications = data?.verifications ?? []
  const needle = search.trim().toLowerCase()

  // Build execution lookup
  const execByRequest = {}
  for (const exec of executions) {
    if (!execByRequest[exec.requestId]) execByRequest[exec.requestId] = exec
  }

  // Apply filters
  const visible = requests.filter((request) => {
    if (needle && !matches(request, needle)) return false
    const exec = execByRequest[request.id]
    switch (filter) {
      case 'pending': return !exec
      case 'executed': return exec && exec.status === 'SUCCESS'
      case 'verified': return exec && exec.verificationStatus === 'VERIFIED'
      case 'unverified': return exec && exec.status === 'SUCCESS' && exec.verificationStatus === 'UNVERIFIED'
      default: return true
    }
  })

  // Counts for chips
  const counts = {
    '': requests.length,
    pending: requests.filter((r) => !execByRequest[r.id]).length,
    executed: requests.filter((r) => execByRequest[r.id]?.status === 'SUCCESS').length,
    verified: requests.filter((r) => execByRequest[r.id]?.verificationStatus === 'VERIFIED').length,
    unverified: requests.filter((r) => {
      const exec = execByRequest[r.id]
      return exec && exec.status === 'SUCCESS' && exec.verificationStatus === 'UNVERIFIED'
    }).length,
  }

  const selected = requests.find((request) => request.id === selectedId)
  const missingSelection = Boolean(selectedId) && !loading && !selected
  const hasFilters = Boolean(filter || needle)
  const noData = !loading && requests.length === 0

  function clearFilters() {
    setSearch('')
    update({ filter: '' })
  }

  function handleExecuted(execution) {
    const success = execution.status === 'SUCCESS'
    setNotice({
      tone: success ? 'success' : 'danger',
      text: success
        ? `${execution.id} — Simulated execution completed for ${execution.requestId}. No real account was changed.`
        : `${execution.id} — Simulated execution failed for ${execution.requestId}. ${execution.failureReason || ''}`,
    })
    reload()
  }

  function handleVerified(result) {
    const verified = result.verification.decision === 'VERIFIED'
    setNotice({
      tone: verified ? 'success' : 'warning',
      text: verified
        ? `${result.verification.id} — Execution ${result.execution.id} has been verified. No real account was changed.`
        : `${result.verification.id} — Execution ${result.execution.id} has been disputed.`,
    })
    reload()
  }

  const header = (
    <PageHeader
      title="Execution and verification"
      description="Pre-execution rechecks, simulated execution results and independent verification of approved requests."
      actions={
        <>
          <button type="button" className="btn btn--secondary" onClick={reload} disabled={loading}>
            <RefreshCw size={16} aria-hidden="true" /> Refresh
          </button>
          <Link to="/requests" className="btn btn--secondary">
            <ClipboardCheck size={16} aria-hidden="true" /> View requests
          </Link>
        </>
      }
    />
  )

  if (error) {
    return (
      <>
        {header}
        <Card><ErrorState error={error} onRetry={reload} /></Card>
      </>
    )
  }

  return (
    <>
      {header}

      <div className={`callout ${role.canApprove ? 'tone-brand' : 'tone-neutral'}`} role="note">
        <ShieldCheck size={18} aria-hidden="true" />
        <p>
          You are acting as <strong>{role.label}</strong>. {role.summary} This is a demo role chosen in the top bar, not real sign-in or authorization.
        </p>
      </div>

      {notice && (
        <div className={`callout tone-${notice.tone}`} role="status">
          <CheckCircle2 size={18} aria-hidden="true" />
          <p>{notice.text}</p>
          <button type="button" className="icon-btn icon-btn--plain" onClick={() => setNotice(null)} aria-label="Dismiss message">
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      )}

      {missingSelection && (
        <div className="callout tone-warning" role="status">
          <p>
            No approved request with the ID <code className="code-chip">{selectedId}</code> was found.
          </p>
          <button type="button" className="btn btn--secondary btn--small" onClick={() => update({ request: '' })}>Dismiss</button>
        </div>
      )}

      <section className="card findings-card" aria-label="Execution">
        {noData ? (
          <EmptyState
            icon={Play}
            title="No approved requests"
            text="Only approved requests appear here. Go to Requests to approve a pending request, then return here to execute it."
            action={<Link to="/requests?status=PENDING" className="btn btn--primary">Go to requests</Link>}
          />
        ) : (
          <>
            <div className="toolbar">
              <div className="toolbar__row">
                <label className="search">
                  <span className="sr-only">Search executions</span>
                  <Search size={16} aria-hidden="true" />
                  <input
                    type="search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search request ID, name, application or account"
                    disabled={loading}
                  />
                </label>
                {hasFilters && (
                  <button type="button" className="btn btn--secondary btn--small" onClick={clearFilters}>
                    <X size={14} aria-hidden="true" /> Clear filters
                  </button>
                )}
              </div>
              <div className="chips" role="group" aria-label="Filter by execution status">
                {FILTER_OPTIONS.map((chip) => {
                  const active = filter === chip.key
                  return (
                    <button
                      key={chip.key || 'all'}
                      type="button"
                      className={`chip tone-brand ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => update({ filter: chip.key })}
                      disabled={loading}
                    >
                      {chip.label} <span className="chip__count">{loading ? '–' : counts[chip.key]}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {!loading && visible.length === 0 ? (
              <EmptyState
                icon={SearchX}
                title="No requests match your filters"
                text="Try a different search term, or clear the filters."
                action={<button type="button" className="btn btn--secondary" onClick={clearFilters}>Clear filters</button>}
              />
            ) : (
              <ExecutionTable
                rows={visible}
                executions={executions}
                loading={loading}
                selectedId={selectedId}
                onOpen={(id) => update({ request: id })}
              />
            )}

            {!loading && (
              <p className="table-foot">
                Showing {visible.length} of {requests.length} approved requests.{' '}
                {IS_DEMO && (data?.persistence === 'memory'
                  ? 'Browser storage is unavailable, so demo data lasts only until you reload the page.'
                  : 'Demo data is saved in this browser only.')}
              </p>
            )}
          </>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        onClose={() => update({ request: '' })}
        title={selected ? `Execute ${selected.id}` : 'Execution details'}
        subtitle={selected && (
          <>
            {selected.snapshot?.employeeName || selected.snapshot?.accountId || 'Unknown employee'}
            {selected.snapshot?.system ? ` in ${selected.snapshot.system}` : ''}
          </>
        )}
      >
        {selected && (
          <ExecutionDetail
            key={selected.id}
            request={selected}
            executions={executions}
            verifications={verifications}
            onExecuted={handleExecuted}
            onVerified={handleVerified}
          />
        )}
      </Drawer>
    </>
  )
}
