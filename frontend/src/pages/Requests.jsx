import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, FilePlus, RefreshCw, RotateCcw, Search, SearchX, ShieldCheck, X } from 'lucide-react'
import { api } from '../services/api.js'
import { IS_DEMO } from '../services/config.js'
import useAsync from '../hooks/useAsync.js'
import { useDemoRole } from '../context/DemoRole.jsx'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import Drawer from '../components/Drawer.jsx'
import RequestDetail from '../components/RequestDetail.jsx'
import RequestsTable from '../components/RequestsTable.jsx'
import { EmptyState, ErrorState } from '../components/States.jsx'
import { REQUEST_STATUSES, STATUS_ORDER, getRequestType } from '../utils/requestMeta.js'

function matches(request, needle) {
  const snapshot = request.snapshot ?? {}
  const haystack = [
    request.id, request.requestedBy, getRequestType(request.requestType).label,
    snapshot.employeeName, snapshot.employeeId, snapshot.system, snapshot.accountId,
  ].filter(Boolean).join(' ').toLowerCase()
  return haystack.includes(needle)
}

// Pending requests first (they need action), then newest first.
function byUrgency(a, b) {
  const aPending = a.status === 'PENDING' ? 0 : 1
  const bPending = b.status === 'PENDING' ? 0 : 1
  return aPending - bPending || Date.parse(b.createdAt) - Date.parse(a.createdAt)
}

export default function Requests() {
  const { data, loading, error, reload } = useAsync(api.getRequests)
  const { role } = useDemoRole()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState(null)
  const [resetting, setResetting] = useState(false)
  const [resetError, setResetError] = useState(null)

  const statusParam = params.get('status')
  const status = STATUS_ORDER.includes(statusParam) ? statusParam : ''
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
  const needle = search.trim().toLowerCase()
  const visible = requests
    .filter((request) => (!status || request.status === status) && (!needle || matches(request, needle)))
    .sort(byUrgency)
  const selected = requests.find((request) => request.id === selectedId)
  const missingSelection = Boolean(selectedId) && !loading && !selected
  const hasFilters = Boolean(status || needle)
  const counts = { total: requests.length }
  for (const key of STATUS_ORDER) counts[key] = requests.filter((request) => request.status === key).length

  function clearFilters() {
    setSearch('')
    update({ status: '' })
  }

  function handleDecided(result) {
    const approved = result.status === 'APPROVED'
    setNotice({
      tone: approved ? 'success' : 'danger',
      text: `${result.id} was ${approved ? 'approved' : 'rejected'}. This is a recorded decision only; no account was changed.`,
    })
    reload()
  }

  async function handleReset() {
    if (!window.confirm('Reset the demo requests? Requests you created in this browser will be removed and the starting examples restored.')) return
    setResetting(true)
    setResetError(null)
    try {
      await api.resetDemoRequests()
      setNotice({ tone: 'success', text: 'Demo requests were reset to the starting examples.' })
      update({ request: '', status: '' })
      setSearch('')
      reload()
    } catch (caught) {
      setResetError(caught)
    } finally {
      setResetting(false)
    }
  }

  const header = (
    <PageHeader
      title="Requests and approvals"
      description="Requests raised from findings, and the decisions made on them. Approving a request records a decision only."
      actions={
        <>
          {IS_DEMO && (
            <button type="button" className="btn btn--secondary" onClick={handleReset} disabled={loading || resetting}>
              <RotateCcw size={16} aria-hidden="true" /> {resetting ? 'Resetting…' : 'Reset demo requests'}
            </button>
          )}
          <button type="button" className="btn btn--secondary" onClick={reload} disabled={loading}>
            <RefreshCw size={16} aria-hidden="true" /> Refresh
          </button>
          <Link to="/findings?classification=LEAVER_ACTIVE" className="btn btn--primary">
            <FilePlus size={16} aria-hidden="true" /> Start from a finding
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

  const noData = !loading && requests.length === 0

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

      {resetError && (
        <div className="callout tone-danger" role="alert">
          <p><strong>The reset did not work.</strong> {resetError.message}</p>
        </div>
      )}

      {missingSelection && (
        <div className="callout tone-warning" role="status">
          <p>
            No request with the ID <code className="code-chip">{selectedId}</code> was found. It may have been removed by resetting the demo requests.
          </p>
          <button type="button" className="btn btn--secondary btn--small" onClick={() => update({ request: '' })}>Dismiss</button>
        </div>
      )}

      <section className="card findings-card" aria-label="Requests">
        {noData ? (
          <EmptyState
            icon={FilePlus}
            title="No requests yet"
            text="Open a finding and choose Start request. Submitted requests appear here with their approval status."
            action={<Link to="/findings?classification=LEAVER_ACTIVE" className="btn btn--primary">Go to findings</Link>}
          />
        ) : (
          <>
            <div className="toolbar">
              <div className="toolbar__row">
                <label className="search">
                  <span className="sr-only">Search requests</span>
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
              <div className="chips" role="group" aria-label="Filter by status">
                {[{ key: '', label: 'All', count: counts.total, tone: 'brand' }, ...STATUS_ORDER.map((key) => ({ key, label: REQUEST_STATUSES[key].label, count: counts[key], tone: REQUEST_STATUSES[key].tone }))].map((chip) => {
                  const active = status === chip.key
                  return (
                    <button
                      key={chip.key || 'all'}
                      type="button"
                      className={`chip tone-${chip.tone} ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => update({ status: chip.key })}
                      disabled={loading}
                    >
                      {chip.label} <span className="chip__count">{loading ? '–' : chip.count}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {!loading && visible.length === 0 ? (
              <EmptyState
                icon={SearchX}
                title={status === 'PENDING' && !needle ? 'No requests are waiting for a decision' : 'No requests match your filters'}
                text={status === 'PENDING' && !needle ? 'Everything has been decided. New requests appear here as soon as they are submitted.' : 'Try a different search term, or clear the filters to see every request again.'}
                action={<button type="button" className="btn btn--secondary" onClick={clearFilters}>Clear filters</button>}
              />
            ) : (
              <RequestsTable
                rows={visible}
                loading={loading}
                selectedId={selectedId}
                canDecide={role.canApprove}
                onOpen={(id) => update({ request: id })}
              />
            )}

            {!loading && (
              <p className="table-foot">
                Showing {visible.length} of {requests.length} requests.{' '}
                {IS_DEMO && (data?.persistence === 'memory'
                  ? 'Browser storage is unavailable, so demo requests last only until you reload the page.'
                  : 'Demo requests are saved in this browser only.')}
              </p>
            )}
          </>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        onClose={() => update({ request: '' })}
        title={selected ? `Request ${selected.id}` : 'Request details'}
        subtitle={selected && (
          <>
            {selected.snapshot?.employeeName || selected.snapshot?.accountId || 'Unknown employee'}
            {selected.snapshot?.system ? ` in ${selected.snapshot.system}` : ''}
          </>
        )}
      >
        {selected && <RequestDetail key={selected.id} request={selected} onDecided={handleDecided} />}
      </Drawer>
    </>
  )
}
