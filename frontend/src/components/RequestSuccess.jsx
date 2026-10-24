import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import Badge from './Badge.jsx'
import { getRequestStatus, getRequestType } from '../utils/requestMeta.js'

export default function RequestSuccess({ request, onBack }) {
  const status = getRequestStatus(request.status)
  return (
    <div className="state state--left" role="status">
      <span className="state__icon tone-success"><CheckCircle2 size={22} aria-hidden="true" /></span>
      <h2>Request submitted</h2>
      <p>
        <code className="code-chip">{request.id}</code> is now waiting for a decision from an approver.
        No account has been changed.
      </p>
      <dl className="kv kv--compact">
        <dt>Type</dt>
        <dd>{getRequestType(request.requestType).label}</dd>
        <dt>Status</dt>
        <dd><Badge tone={status.tone}>{status.label}</Badge></dd>
      </dl>
      <div className="form__actions">
        <button type="button" className="btn btn--secondary" onClick={onBack}>Back to finding</button>
        <Link to={`/requests?request=${encodeURIComponent(request.id)}`} className="btn btn--primary">Open in Requests</Link>
      </div>
    </div>
  )
}
