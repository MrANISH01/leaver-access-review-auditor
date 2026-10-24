import { ChevronRight } from 'lucide-react'
import Badge from './Badge.jsx'
import NotAvailable from './NotAvailable.jsx'
import { Skeleton } from './States.jsx'
import { getClassification } from '../utils/classifications.js'
import { getRequestType } from '../utils/requestMeta.js'
import { getExecutionStatus, getVerificationStatus } from '../utils/executionMeta.js'
import { formatDateTime, formatRelative } from '../utils/format.js'

const COLUMNS = ['Request', 'Employee', 'Application and account', 'Type', 'Execution', 'Verification', 'Executed']
const SKELETON_ROWS = 4

function ExecutionRow({ request, execution, selected, onOpen }) {
  const snapshot = request.snapshot ?? {}
  const classification = snapshot.classification ? getClassification(snapshot.classification) : null
  const label = snapshot.employeeName || snapshot.accountId || request.id

  const execStatus = execution ? getExecutionStatus(execution.status) : { label: 'Not started', tone: 'neutral' }
  const verStatus = execution ? getVerificationStatus(execution.verificationStatus) : { label: '—', tone: 'neutral' }
  const needsAction = !execution
  const needsVerification = execution?.status === 'SUCCESS' && execution?.verificationStatus === 'UNVERIFIED'

  return (
    <tr className={selected ? 'is-selected' : ''} onClick={() => onOpen(request.id)}>
      <td>
        <div className="identity">
          <span className="identity__name"><code className="code-chip">{request.id}</code></span>
          <span className="identity__id">
            <time dateTime={request.decidedAt} title={formatDateTime(request.decidedAt)}>{formatRelative(request.decidedAt)}</time>
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
      <td><Badge tone={execStatus.tone}>{execStatus.label}</Badge></td>
      <td><Badge tone={verStatus.tone}>{verStatus.label}</Badge></td>
      <td>
        {execution?.executedAt
          ? <time dateTime={execution.executedAt} title={formatDateTime(execution.executedAt)}>{formatRelative(execution.executedAt)}</time>
          : <span className="muted">Not yet</span>}
      </td>
      <td className="table__action">
        <button
          type="button"
          className={`btn btn--small ${needsAction || needsVerification ? 'btn--primary' : 'btn--secondary'}`}
          aria-label={`${needsAction ? 'Execute' : needsVerification ? 'Verify' : 'View'} request ${request.id} for ${label}`}
          onClick={(event) => { event.stopPropagation(); onOpen(request.id) }}
        >
          {needsAction ? 'Execute' : needsVerification ? 'Verify' : 'View'} <ChevronRight size={14} aria-hidden="true" />
        </button>
      </td>
    </tr>
  )
}

export default function ExecutionTable({ rows, executions, loading, selectedId, onOpen }) {
  // Map executions by requestId for quick lookup
  const execByRequest = {}
  for (const exec of executions) {
    // Keep the latest (first in array, which is newest)
    if (!execByRequest[exec.requestId]) {
      execByRequest[exec.requestId] = exec
    }
  }

  return (
    <div className="table-wrap" role="region" aria-label="Execution table" tabIndex={0}>
      <table className="table table--execution" aria-busy={loading}>
        <caption className="sr-only">Approved requests eligible for execution, with their execution and verification status.</caption>
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
                <ExecutionRow
                  key={request.id}
                  request={request}
                  execution={execByRequest[request.id]}
                  selected={request.id === selectedId}
                  onOpen={onOpen}
                />
              ))}
        </tbody>
      </table>
    </div>
  )
}
