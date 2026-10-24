import { ChevronDown, ChevronRight, ChevronUp, ChevronsUpDown, FilePlus } from 'lucide-react'
import Badge from './Badge.jsx'
import Confidence from './Confidence.jsx'
import NotAvailable from './NotAvailable.jsx'
import { Skeleton } from './States.jsx'
import { getClassification } from '../utils/classifications.js'
import { getReviewStatus, getSeverity } from '../utils/findingMeta.js'
import { getRequestEligibility } from '../utils/requestMeta.js'
import { SORT_COLUMNS } from '../utils/findingsQuery.js'
import { formatDateTime, formatRelative } from '../utils/format.js'

const COLUMNS = Object.entries(SORT_COLUMNS).map(([key, column]) => ({ key, label: column.label }))
const SKELETON_ROWS = 6

function SortIcon({ active, dir }) {
  if (!active) return <ChevronsUpDown size={14} aria-hidden="true" />
  return dir === 'asc' ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />
}

function FindingRow({ finding, selected, onInspect, onRequest }) {
  const classification = getClassification(finding.classification)
  const severity = getSeverity(finding.severity)
  const status = getReviewStatus(finding.reviewStatus)
  const name = finding.employeeName || finding.accountId || 'this account'
  const canRequest = getRequestEligibility(finding).allowed

  return (
    <tr className={selected ? 'is-selected' : ''} onClick={() => onInspect(finding.id)}>
      <td>
        <div className="identity">
          <span className="identity__name">{finding.employeeName || <NotAvailable />}</span>
          {finding.employeeId && <span className="identity__id">{finding.employeeId}</span>}
        </div>
      </td>
      <td>{finding.system || <NotAvailable />}</td>
      <td>{finding.accountId ? <code className="code-chip">{finding.accountId}</code> : <NotAvailable />}</td>
      <td><Badge tone={classification.tone} icon={classification.icon}>{classification.label}</Badge></td>
      <td>{severity ? <Badge tone={severity.tone}>{severity.label}</Badge> : <NotAvailable />}</td>
      <td><Confidence value={finding.matchConfidence} /></td>
      <td>{status ? <Badge tone={status.tone}>{status.label}</Badge> : <NotAvailable />}</td>
      <td>
        {finding.lastSeenAt
          ? <time dateTime={finding.lastSeenAt} title={formatDateTime(finding.lastSeenAt)}>{formatRelative(finding.lastSeenAt)}</time>
          : <NotAvailable />}
      </td>
      <td className="table__action">
        <div className="row-actions">
          {canRequest && (
            <button
              type="button"
              className="btn btn--secondary btn--small"
              aria-label={`Start a request for ${name}`}
              onClick={(event) => { event.stopPropagation(); onRequest(finding.id) }}
            >
              <FilePlus size={14} aria-hidden="true" /> Request
            </button>
          )}
          <button
            type="button"
            className="btn btn--secondary btn--small"
            aria-label={`Inspect finding for ${name}`}
            onClick={(event) => { event.stopPropagation(); onInspect(finding.id) }}
          >
            Inspect <ChevronRight size={14} aria-hidden="true" />
          </button>
        </div>
      </td>
    </tr>
  )
}

export default function FindingsTable({ rows, loading, sortKey, sortDir, onSort, onInspect, onRequest, selectedId }) {
  return (
    <div className="table-wrap" role="region" aria-label="Findings table" tabIndex={0}>
      <table className="table" aria-busy={loading}>
        <caption className="sr-only">Findings from the leaver access audit. Use the column buttons to sort.</caption>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              const active = column.key === sortKey
              return (
                <th key={column.key} scope="col" aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  <button type="button" className="th-sort" onClick={() => onSort(column.key)} disabled={loading}>
                    {column.label}
                    <SortIcon active={active} dir={sortDir} />
                  </button>
                </th>
              )
            })}
            <th scope="col"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: SKELETON_ROWS }, (_, row) => (
                <tr key={row} className="is-skeleton">
                  {Array.from({ length: COLUMNS.length + 1 }, (__, cell) => (
                    <td key={cell}><Skeleton height={16} width={cell === 0 ? '80%' : '60%'} /></td>
                  ))}
                </tr>
              ))
            : rows.map((finding) => (
                <FindingRow key={finding.id} finding={finding} selected={finding.id === selectedId} onInspect={onInspect} onRequest={onRequest} />
              ))}
        </tbody>
      </table>
    </div>
  )
}
