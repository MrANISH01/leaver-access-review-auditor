import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Info, ShieldCheck, X } from 'lucide-react'
import { api } from '../services/api.js'
import { IS_DEMO } from '../services/config.js'
import { useDemoRole } from '../context/DemoRole.jsx'
import Badge from './Badge.jsx'
import NotAvailable from './NotAvailable.jsx'
import { getClassification } from '../utils/classifications.js'
import { getSeverity } from '../utils/findingMeta.js'
import { TEXT_MAX, getPriority, getRequestStatus, getRequestType } from '../utils/requestMeta.js'
import { formatDateTime } from '../utils/format.js'

function Section({ title, tag, children }) {
  return (
    <section className="detail__section">
      <div className="detail__head">
        <h3>{title}</h3>
        {tag && <span className={`tag tag--${tag.kind}`}>{tag.label}</span>}
      </div>
      {children}
    </section>
  )
}

function Fact({ label, children }) {
  const empty = children === null || children === undefined || children === false || children === ''
  return (
    <>
      <dt>{label}</dt>
      <dd>{empty ? <NotAvailable /> : children}</dd>
    </>
  )
}

// Approve / reject controls. They only appear for a pending request, and only for a demo approver
// who did not raise the request. The mock adapter checks the same rules again.
function DecisionForm({ request, onDecided }) {
  const { role } = useDemoRole()
  const ids = useId()
  const [comment, setComment] = useState('')
  const [working, setWorking] = useState(null)
  const [error, setError] = useState(null)
  const [commentProblem, setCommentProblem] = useState('')

  async function decide(decision) {
    if (working) return
    if (decision === 'REJECTED' && !comment.trim()) {
      setCommentProblem('Add a comment explaining why the request is rejected.')
      return
    }
    setCommentProblem('')
    setWorking(decision)
    setError(null)
    try {
      const updated = await api.decideRequest({ requestId: request.id, decision, comment, actorId: role.id })
      onDecided(updated)
    } catch (caught) {
      setError(caught)
      setWorking(null)
    }
  }

  return (
    <div className="form">
      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-comment`}>
          Comment <span className="form__optional">(optional for approval, required for rejection)</span>
        </label>
        <textarea
          id={`${ids}-comment`}
          className={`input ${commentProblem ? 'is-invalid' : ''}`}
          rows={3}
          maxLength={TEXT_MAX}
          value={comment}
          onChange={(event) => { setComment(event.target.value); if (commentProblem) setCommentProblem('') }}
          aria-invalid={Boolean(commentProblem)}
          aria-describedby={`${ids}-comment-hint`}
          disabled={Boolean(working)}
        />
        <p id={`${ids}-comment-hint`} className={`form__hint ${commentProblem ? 'form__hint--error' : ''}`}>
          {commentProblem || 'Your comment is saved with the decision.'}
        </p>
      </div>

      {error && (
        <div className="callout tone-danger" role="alert">
          <p><strong>The decision was not saved.</strong> {error.message}</p>
        </div>
      )}

      <div className="form__actions">
        <button type="button" className="btn btn--danger" onClick={() => decide('REJECTED')} disabled={Boolean(working)}>
          <X size={16} aria-hidden="true" /> {working === 'REJECTED' ? 'Rejecting…' : 'Reject'}
        </button>
        <button type="button" className="btn btn--success" onClick={() => decide('APPROVED')} disabled={Boolean(working)}>
          <Check size={16} aria-hidden="true" /> {working === 'APPROVED' ? 'Approving…' : 'Approve'}
        </button>
      </div>
    </div>
  )
}

function DecisionPanel({ request, onDecided }) {
  const { role } = useDemoRole()
  if (!role.canApprove) {
    return (
      <div className="callout tone-neutral" role="note">
        <Info size={18} aria-hidden="true" />
        <p>You are acting as <strong>{role.label}</strong>, who cannot decide requests. Switch the demo role to <strong>Demo approver</strong> in the top bar to approve or reject this one.</p>
      </div>
    )
  }
  if (request.requestedBy === role.id) {
    return (
      <div className="callout tone-neutral" role="note">
        <Info size={18} aria-hidden="true" />
        <p>You raised this request as <strong>{role.label}</strong>, so a different reviewer must decide it. Switch to <strong>Demo analyst</strong> to raise requests, and <strong>Demo approver</strong> to decide requests raised by someone else.</p>
      </div>
    )
  }
  return <DecisionForm request={request} onDecided={onDecided} />
}

export default function RequestDetail({ request, onDecided }) {
  // After a decision this panel shows the updated request straight away, before the list reloads.
  const [updated, setUpdated] = useState(null)
  const current = updated ?? request
  const status = getRequestStatus(current.status)
  const priority = getPriority(current.priority)
  const snapshot = current.snapshot ?? {}
  const classification = snapshot.classification ? getClassification(snapshot.classification) : null
  const severity = getSeverity(snapshot.severity)
  const decided = current.status !== 'PENDING'

  function handleDecided(result) {
    setUpdated(result)
    onDecided(result)
  }

  return (
    <div className="detail">
      <div className="detail__badges">
        <Badge tone={status.tone}>{status.label}</Badge>
        {priority && <Badge tone={priority.tone}>{priority.label} priority</Badge>}
        <Badge tone="neutral">{getRequestType(current.requestType).label}</Badge>
      </div>

      {IS_DEMO && <p className="note tone-warning">Synthetic demo request. It does not describe a real person or account.</p>}

      <div className="callout tone-brand" role="note">
        <ShieldCheck size={18} aria-hidden="true" />
        <p>
          <strong>Decision only.</strong> Approving or rejecting records a decision in this demo. No account is disabled or changed.
        </p>
      </div>

      <Section title="Request">
        <dl className="kv">
          <Fact label="Request ID"><code className="code-chip">{current.id}</code></Fact>
          <Fact label="Type">{getRequestType(current.requestType).label}</Fact>
          <Fact label="Priority">{priority?.label}</Fact>
          <Fact label="Reason">{current.reason ? <span className="prewrap">{current.reason}</span> : null}</Fact>
          <Fact label="Additional notes">{current.notes ? <span className="prewrap">{current.notes}</span> : null}</Fact>
          <Fact label="Requested by">{current.requestedBy ? <code className="code-chip">{current.requestedBy}</code> : null}</Fact>
          <Fact label="Requested at">{current.createdAt ? formatDateTime(current.createdAt) : null}</Fact>
        </dl>
      </Section>

      <Section title="Finding at the time of the request" tag={{ kind: 'observed', label: 'Observed' }}>
        <dl className="kv">
          <Fact label="Employee">{snapshot.employeeName}</Fact>
          <Fact label="Employee ID">{snapshot.employeeId}</Fact>
          <Fact label="Application">{snapshot.system}</Fact>
          <Fact label="Account">{snapshot.accountId ? <code className="code-chip">{snapshot.accountId}</code> : null}</Fact>
          <Fact label="Classification">{classification ? <Badge tone={classification.tone} icon={classification.icon}>{classification.label}</Badge> : null}</Fact>
          <Fact label="Severity">{severity ? <Badge tone={severity.tone}>{severity.label}</Badge> : null}</Fact>
        </dl>
        {current.findingId && (
          <p className="detail__link">
            <Link to={`/findings?finding=${encodeURIComponent(current.findingId)}`}>Open this finding</Link>
          </p>
        )}
      </Section>

      <Section title="Decision">
        {decided ? (
          <dl className="kv">
            <Fact label="Outcome"><Badge tone={status.tone}>{status.label}</Badge></Fact>
            <Fact label="Decided by">{current.decidedBy ? <code className="code-chip">{current.decidedBy}</code> : null}</Fact>
            <Fact label="Decided at">{current.decidedAt ? formatDateTime(current.decidedAt) : null}</Fact>
            <Fact label="Comment">{current.decisionComment ? <span className="prewrap">{current.decisionComment}</span> : <span className="muted">No comment was added.</span>}</Fact>
          </dl>
        ) : (
          <>
            <p className="detail__hint">Awaiting a decision from a demo approver.</p>
            <DecisionPanel request={current} onDecided={handleDecided} />
          </>
        )}
      </Section>
    </div>
  )
}
