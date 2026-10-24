import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { RefreshCw, SearchX } from 'lucide-react'
import { api } from '../services/api.js'
import useAsync from '../hooks/useAsync.js'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import Drawer from '../components/Drawer.jsx'
import FindingDetail from '../components/FindingDetail.jsx'
import FindingRequestAction from '../components/FindingRequestAction.jsx'
import RequestForm from '../components/RequestForm.jsx'
import RequestSuccess from '../components/RequestSuccess.jsx'
import FindingsTable from '../components/FindingsTable.jsx'
import FindingsToolbar from '../components/FindingsToolbar.jsx'
import Pagination from '../components/Pagination.jsx'
import { EmptyState, ErrorState } from '../components/States.jsx'
import { getRequestEligibility } from '../utils/requestMeta.js'
import {
  SORT_COLUMNS, countByClassification, distinctValues, filterFindings, paginate, readQuery, sortFindings,
} from '../utils/findingsQuery.js'

export default function Findings() {
  const { data, loading, error, reload } = useAsync(api.getFindings)
  const [params, setParams] = useSearchParams()
  // The search box text lives in React state (typing is too frequent for the address bar).
  // Everything else lives in the address bar, so links like /findings?classification=OK work.
  const [search, setSearch] = useState('')
  // Set right after a request is submitted so the drawer can show a confirmation.
  const [submitted, setSubmitted] = useState(null)
  const query = readQuery(params)
  // ?finding=F-001&request=new opens the drawer on the request form, so it survives a refresh.
  const requestMode = params.get('request') === 'new'

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

  const findings = data?.findings ?? []
  const filtered = sortFindings(filterFindings(findings, { ...query, q: search }), { key: query.sortKey, dir: query.sortDir })
  const view = paginate(filtered, query.page)
  const selected = findings.find((item) => item.id === query.selectedId)
  const hasFilters = Boolean(search.trim() || query.classification || query.system || query.status)
  const showForm = Boolean(selected) && requestMode && getRequestEligibility(selected).allowed
  const showSuccess = Boolean(selected) && submitted?.findingId === selected.id

  function closeDrawer() {
    setSubmitted(null)
    update({ finding: '', request: '' })
  }

  function handleSubmitted(request) {
    setSubmitted(request)
    update({ request: '' })
    reload()
  }

  function handleSearch(value) {
    setSearch(value)
    if (query.page !== 1) update({ page: '' })
  }

  function handleSort(key) {
    const dir = query.sortKey === key ? (query.sortDir === 'asc' ? 'desc' : 'asc') : SORT_COLUMNS[key].defaultDir
    update({ sort: key, dir, page: '' })
  }

  function clearFilters() {
    setSearch('')
    update({ classification: '', system: '', status: '', page: '' })
  }

  const header = (
    <PageHeader
      title="Findings and access review"
      description="Every account the audit reviewed, with the evidence behind each classification. Select a row to inspect it."
      actions={
        <button type="button" className="btn btn--secondary" onClick={reload} disabled={loading}>
          <RefreshCw size={16} aria-hidden="true" /> Refresh
        </button>
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

  const noData = !loading && findings.length === 0

  return (
    <>
      {header}

      <section className="card findings-card" aria-label="Findings">
        {noData ? (
          <EmptyState title="No findings yet" text="Nothing has been classified yet. Findings appear here after a scan completes." />
        ) : (
          <>
            <FindingsToolbar
              disabled={loading}
              counts={countByClassification(findings)}
              search={search}
              onSearch={handleSearch}
              classification={query.classification}
              onClassification={(value) => update({ classification: value, page: '' })}
              system={query.system}
              systems={distinctValues(findings, (item) => item.system)}
              onSystem={(value) => update({ system: value, page: '' })}
              status={query.status}
              statuses={distinctValues(findings, (item) => item.reviewStatus)}
              onStatus={(value) => update({ status: value, page: '' })}
              hasFilters={hasFilters}
              onClear={clearFilters}
            />

            {!loading && view.total === 0 ? (
              <EmptyState
                icon={SearchX}
                title="No findings match your filters"
                text="Try a different search term, or clear the filters to see every finding again."
                action={<button type="button" className="btn btn--secondary" onClick={clearFilters}>Clear filters</button>}
              />
            ) : (
              <FindingsTable
                rows={view.items}
                loading={loading}
                sortKey={query.sortKey}
                sortDir={query.sortDir}
                onSort={handleSort}
                onInspect={(id) => update({ finding: id, request: '' })}
                onRequest={(id) => update({ finding: id, request: 'new' })}
                selectedId={query.selectedId}
              />
            )}

            {!loading && view.total > 0 && (
              <Pagination
                page={view.page}
                pageCount={view.pageCount}
                start={view.start}
                end={view.end}
                total={view.total}
                allTotal={findings.length}
                onChange={(page) => update({ page: page === 1 ? '' : page })}
              />
            )}
          </>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        onClose={closeDrawer}
        title={showForm ? 'Start a request' : showSuccess ? 'Request submitted' : selected?.employeeName || selected?.accountId || 'Finding details'}
        subtitle={selected && (
          <>
            <code className="code-chip">{selected.accountId || 'No account ID'}</code> in {selected.system || 'an unknown application'}
          </>
        )}
        footer={selected && !showForm && !showSuccess
          ? <FindingRequestAction finding={selected} onStart={() => update({ request: 'new' })} />
          : null}
      >
        {selected && (showSuccess
          ? <RequestSuccess request={submitted} onBack={() => setSubmitted(null)} />
          : showForm
            ? <RequestForm key={selected.id} finding={selected} onCancel={() => update({ request: '' })} onSubmitted={handleSubmitted} />
            : <FindingDetail finding={selected} />)}
      </Drawer>
    </>
  )
}
