import { useState } from 'react'
import { Download, RefreshCw, ScrollText, Search, SearchX } from 'lucide-react'
import { api } from '../services/api.js'
import useAsync from '../hooks/useAsync.js'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import { EmptyState, ErrorState, Skeleton } from '../components/States.jsx'
import { eventsToCsv, getEventMeta, getEventOutcome, listEventTypes, listOutcomes } from '../utils/auditEvents.js'
import { formatDateTime } from '../utils/format.js'
import { getRoleById } from '../utils/demoRoles.js'

function matches(event, needle) {
  return [event.requestId, event.subject, event.id].filter(Boolean).join(' ').toLowerCase().includes(needle)
}

function downloadCsv(events) {
  const blob = new Blob(['﻿', eventsToCsv(events)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `leaverguard-audit-trail-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function AuditTrail() {
  const { data, loading, error, reload } = useAsync(api.getAuditTrail)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [outcome, setOutcome] = useState('')

  const events = data?.events ?? []
  const needle = search.trim().toLowerCase()
  const visible = events.filter((event) =>
    (!type || event.type === type) &&
    (!outcome || getEventOutcome(event.type).key === outcome) &&
    (!needle || matches(event, needle)))
  const hasFilters = Boolean(type || outcome || needle)

  function clearFilters() {
    setSearch('')
    setType('')
    setOutcome('')
  }

  const header = (
    <PageHeader
      title="Audit trail"
      description="A chronological record of what happened and who performed each recorded action. Demo roles are labels, not real sign-in."
      actions={
        <>
          <button type="button" className="btn btn--secondary" onClick={reload} disabled={loading}>
            <RefreshCw size={16} aria-hidden="true" /> Refresh
          </button>
          <button type="button" className="btn btn--primary" onClick={() => downloadCsv(visible)} disabled={loading || visible.length === 0}>
            <Download size={16} aria-hidden="true" /> Export CSV
          </button>
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
      <section className="card">
        <div className="toolbar">
          <div className="toolbar__row">
            <label className="search">
              <Search size={16} aria-hidden="true" />
              <input
                type="search" value={search} onChange={(e) => setSearch(e.target.value)} disabled={loading}
                placeholder="Search by request ID, e.g. REQ-DEMO-003" aria-label="Search by request ID or reference"
              />
            </label>
            <label className="field">
              <span className="sr-only">Event type</span>
              <select value={type} onChange={(e) => setType(e.target.value)} disabled={loading}>
                <option value="">All event types</option>
                {listEventTypes().map((item) => <option key={item.type} value={item.type}>{item.label}</option>)}
              </select>
            </label>
            <label className="field">
              <span className="sr-only">Outcome</span>
              <select value={outcome} onChange={(e) => setOutcome(e.target.value)} disabled={loading}>
                <option value="">All outcomes</option>
                {listOutcomes().map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
              </select>
            </label>
            {hasFilters && <button type="button" className="btn btn--secondary" onClick={clearFilters}>Clear filters</button>}
          </div>
        </div>

        {loading ? (
          <div className="card__body" aria-busy="true">
            {[0, 1, 2, 3].map((n) => <div key={n} style={{ marginBottom: 14 }}><Skeleton height={20} /></div>)}
          </div>
        ) : events.length === 0 ? (
          <EmptyState icon={ScrollText} title="No audit events recorded yet"
            text="Events appear here after a request is submitted, decided, executed or verified." />
        ) : visible.length === 0 ? (
          <EmptyState icon={SearchX} title="No events match these filters" text="Try a different request ID, event type or outcome."
            action={<button type="button" className="btn btn--secondary" onClick={clearFilters}>Clear filters</button>} />
        ) : (
          <>
            <div className="table-wrap" tabIndex={0}>
              <table className="table table--audit">
                <caption className="sr-only">Audit events, newest first.</caption>
                <thead>
                  <tr>
                    <th scope="col">Time</th><th scope="col">Event</th><th scope="col">Outcome</th>
                    <th scope="col">Request</th><th scope="col">Actor</th><th scope="col">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((event) => {
                    const meta = getEventMeta(event.type)
                    const result = getEventOutcome(event.type)
                    const Icon = meta.icon
                    const actor = getRoleById(event.actor)
                    return (
                      <tr key={event.id}>
                        <td className="nowrap"><time dateTime={event.timestamp}>{formatDateTime(event.timestamp)}</time></td>
                        <td><span className={`audit-type tone-${meta.tone}`}><Icon size={16} aria-hidden="true" />{meta.label}</span></td>
                        <td><span className={`pill tone-${result.tone}`}>{result.label}</span></td>
                        <td>
                          {event.requestId ? <code className="code-chip">{event.requestId}</code> : <span className="na">None</span>}
                          {event.subject && event.subject !== event.requestId && (
                            <div className="status-meta"><code className="code-chip">{event.subject}</code></div>
                          )}
                        </td>
                        <td>{event.actor ? <span className="actor-chip">{actor?.label ?? event.actor}</span> : <span className="na">Not available</span>}</td>
                        <td className="audit-details">{event.details || <span className="na">No details recorded</span>}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="table-foot">
              Showing {visible.length} of {events.length} recorded events. The CSV export contains the events currently shown.
            </p>
          </>
        )}
      </section>
    </>
  )
}
