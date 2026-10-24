import { ChevronRight } from 'lucide-react'
import Badge from './Badge.jsx'
import NotAvailable from './NotAvailable.jsx'
import { Skeleton } from './States.jsx'
import { getClassification } from '../utils/classifications.js'
import { getPriority, getRequestStatus, getRequestType } from '../utils/requestMeta.js'
import { formatDateTime, formatRelative } from '../utils/format.js'

const COLUMNS = ['Request', 'Employee', 'Application and account', 'Type', 'Priority', 'Status', 'Requested by', 'Decision']
const SKELETON_ROWS = 4

function RequestRow({ request, selected, canDecide, onOpen }) {
  const status = getRequestStatus(request.status)
  const priority = getPriority(request.priority)
  const snapshot = request.snapshot ?? {}
  const classification = snapshot.classification ? getClassification(snapshot.classification) : null
  const label = snapshot.employeeName || snapshot.accountId || request.id
  const pending = request.status === 'PENDING'

  return (
    <tr className={selected ? 'is-selected' : ''} onClick={() => onOpen(request.id)}>
      <td>
        <div className="identity">
          <span className="identity__name"><code className="code-chip">{request.id}</code></span>
          <span className="identity__id">
            <time dateTime={request.createdAt} title={formatDateTime(request.createdAt)}>{formatRelative(request.createdAt)}</time>
          </span>
        </div>
      </td>
      <td>
        <div className="identity">
          <span className="identity__name">{snapshot.employeeName || <NotAvailable />}</span>
          {snapshot.employeeId && <span className="identity__id">{snapshot.employeeId}</span>}
        </div>
      </td>
      <td>
        <div className="identity">
          <span>{snapshot.system || <NotAvailable />}</span>
          <span className="identity__id">{snapshot.accountId || 'No account ID'}</span>
        </div>
      </td>
      <td>
        <div className="identity">
          <span>{getRequestType(request.requestType).label}</span>
          {classification && <span className="identity__id">{classification.label}</span>}
        </div>
      </td>
      <td>{priority ? <Badge tone={priority.tone}>{priority.label}</Badge> : <NotAvailable />}</td>
      <td><Badge tone={status.tone}>{status.label}</Badge></td>
      <td>{request.requestedBy ? <code className="code-chip">{request.requestedBy}</code> : <NotAvailable />}</td>
      <td>
        {pending
          ? <span className="muted">Awaiting decision</span>
          : request.decidedAt
            ? <time dateTime={request.decidedAt} title={formatDateTime(request.decidedAt)}>{formatRelative(request.decidedAt)}</time>
            : <NotAvailable />}
      </td>
      <td className="table__action">
        <button
          type="button"
          className={`btn btn--small ${pending && canDecide ? 'btn--primary' : 'btn--secondary'}`}
          aria-label={`${pending && canDecide ? 'Review' : 'View'} request ${request.id} for ${label}`}
          onClick={(event) => { event.stopPropagation(); onOpen(request.id) }}
        >
          {pending && canDecide ? 'Review' : 'View'} <ChevronRight size={14} aria-hidden="true" />
        </button>
      </td>
    </tr>
  )
}

export default function RequestsTable({ rows, loading, selectedId, canDecide, onOpen }) {
  return (
    <div className="table-wrap" role="region" aria-label="Requests table" tabIndex={0}>
      <table className="table table--requests" aria-busy={loading}>
        <caption className="sr-only">Requests raised from findings, with their approval status.</caption>
        <thead>
          <tr>
            {COLUMNS.map((label) => <th key={label} scope="col">{label}</th>)}
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
            : rows.map((request) => (
                <RequestRow key={request.id} request={request} selected={request.id === selectedId} canDecide={canDecide} onOpen={onOpen} />
              ))}
        </tbody>
      </table>
    </div>
  )
}
