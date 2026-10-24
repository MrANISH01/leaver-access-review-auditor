import { useId, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { api } from '../services/api.js'
import { useDemoRole } from '../context/DemoRole.jsx'
import Badge from './Badge.jsx'
import NotAvailable from './NotAvailable.jsx'
import { getClassification } from '../utils/classifications.js'
import { PRIORITIES, REASON_MIN, REQUEST_TYPES, TEXT_MAX, defaultRequestType } from '../utils/requestMeta.js'

// The form for starting a request from one finding. It only records a request for approval.
export default function RequestForm({ finding, onCancel, onSubmitted }) {
  const { role } = useDemoRole()
  const ids = useId()
  const [requestType, setRequestType] = useState(defaultRequestType(finding.classification))
  const [priority, setPriority] = useState('normal')
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const classification = getClassification(finding.classification)
  const reasonLength = reason.trim().length
  const reasonProblem = reasonLength < REASON_MIN ? `Give a reason of at least ${REASON_MIN} characters.` : ''
  const showReasonProblem = touched && reasonProblem

  async function handleSubmit(event) {
    event.preventDefault()
    setTouched(true)
    if (reasonProblem || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const request = await api.createRequest({
        findingId: finding.id, requestType, priority, reason, notes, actorId: role.id,
      })
      onSubmitted(request)
    } catch (caught) {
      setError(caught)
      setSubmitting(false)
    }
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <section className="form__summary" aria-label="Finding this request is about">
        <dl className="kv">
          <dt>Employee</dt>
          <dd>{finding.employeeName || <NotAvailable />}</dd>
          <dt>Application</dt>
          <dd>{finding.system || <NotAvailable />}</dd>
          <dt>Account</dt>
          <dd>{finding.accountId ? <code className="code-chip">{finding.accountId}</code> : <NotAvailable />}</dd>
          <dt>Classification</dt>
          <dd><Badge tone={classification.tone} icon={classification.icon}>{classification.label}</Badge></dd>
        </dl>
      </section>

      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-type`}>Request type</label>
        <select id={`${ids}-type`} className="input" value={requestType} onChange={(event) => setRequestType(event.target.value)} disabled={submitting} autoFocus>
          {Object.entries(REQUEST_TYPES).map(([key, type]) => <option key={key} value={key}>{type.label}</option>)}
        </select>
        <p className="form__hint">{REQUEST_TYPES[requestType].description}</p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-priority`}>Priority</label>
        <select id={`${ids}-priority`} className="input" value={priority} onChange={(event) => setPriority(event.target.value)} disabled={submitting}>
          {Object.entries(PRIORITIES).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
        </select>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-reason`}>Reason <span className="form__required">(required)</span></label>
        <textarea
          id={`${ids}-reason`}
          className={`input ${showReasonProblem ? 'is-invalid' : ''}`}
          rows={4}
          maxLength={TEXT_MAX}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          onBlur={() => setTouched(true)}
          aria-invalid={Boolean(showReasonProblem)}
          aria-describedby={`${ids}-reason-hint`}
          placeholder="Why should this request be approved? Describe what you checked."
          disabled={submitting}
        />
        <p id={`${ids}-reason-hint`} className={`form__hint ${showReasonProblem ? 'form__hint--error' : ''}`}>
          {showReasonProblem || `${reason.length} of ${TEXT_MAX} characters`}
        </p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-notes`}>Additional notes <span className="form__optional">(optional)</span></label>
        <textarea
          id={`${ids}-notes`}
          className="input"
          rows={3}
          maxLength={TEXT_MAX}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Anything the approver should know, such as a handover or a business impact."
          disabled={submitting}
        />
      </div>

      <div className="callout tone-brand" role="note">
        <ShieldCheck size={18} aria-hidden="true" />
        <p>
          Submitting only <strong>records a request for approval</strong>. No account is disabled or changed.
          You are submitting as <strong>{role.label}</strong> (<code className="code-chip">{role.id}</code>), a demo label rather than a signed-in user.
        </p>
      </div>

      {error && (
        <div className="callout tone-danger" role="alert">
          <p><strong>The request was not submitted.</strong> {error.message}</p>
        </div>
      )}

      <div className="form__actions">
        <button type="button" className="btn btn--secondary" onClick={onCancel} disabled={submitting}>Cancel</button>
        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? 'Submitting…' : 'Submit request'}
        </button>
      </div>
    </form>
  )
}
