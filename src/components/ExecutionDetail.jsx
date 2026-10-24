import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Check, CheckCircle2, Info, Play, ShieldCheck, X, XCircle } from 'lucide-react'
import { api } from '../services/api.js'
import { IS_DEMO } from '../services/config.js'
import { useDemoRole } from '../context/DemoRole.jsx'
import Badge from './Badge.jsx'
import NotAvailable from './NotAvailable.jsx'
import { getClassification } from '../utils/classifications.js'
import { getSeverity } from '../utils/findingMeta.js'
import { getRequestType, getRequestStatus, TEXT_MAX } from '../utils/requestMeta.js'
import { getExecutionStatus, getVerificationStatus, runPreExecutionChecks, allChecksPassed } from '../utils/executionMeta.js'
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

function PreChecksList({ checks }) {
  return (
    <ul className="pre-checks">
      {checks.map((check, i) => (
        <li key={i} className={`pre-check ${check.passed ? 'pre-check--pass' : 'pre-check--fail'}`}>
          <span className="pre-check__icon">
            {check.passed
              ? <CheckCircle2 size={16} aria-hidden="true" />
              : <XCircle size={16} aria-hidden="true" />}
          </span>
          <span className="pre-check__text">
            <strong>{check.label}</strong>: {check.reason}
          </span>
        </li>
      ))}
    </ul>
  )
}

function ExecuteForm({ request, executions, onExecuted }) {
  const { role } = useDemoRole()
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(null)
  const [simulateFailure, setSimulateFailure] = useState(false)
  const simFailId = useId()

  const checks = runPreExecutionChecks(request, executions)
  const canExecute = allChecksPassed(checks)

  async function handleExecute() {
    if (working) return
    setWorking(true)
    setError(null)
    try {
      const execution = await api.executeRequest({
        requestId: request.id,
        actorId: role.id,
        simulateFailure,
      })
      onExecuted(execution)
    } catch (caught) {
      setError(caught)
    } finally {
      setWorking(false)
    }
  }

  return (
    <div className="form">
      <Section title="Pre-execution checks">
        <PreChecksList checks={checks} />
      </Section>

      {error && (
        <div className="callout tone-danger" role="alert">
          <p><strong>Execution failed.</strong> {error.message}</p>
        </div>
      )}

      {canExecute ? (
        <>
          <div className="callout tone-brand" role="note">
            <ShieldCheck size={18} aria-hidden="true" />
            <p>
              <strong>Simulated execution.</strong> Clicking the button below records the execution in this demo. No real account will be disabled or changed.
            </p>
          </div>

          <div className="form__field">
            <label className="checkbox-label">
              <input
                type="checkbox"
                id={simFailId}
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                disabled={working}
              />
              <span>Simulate a failure (for testing)</span>
            </label>
          </div>

          <div className="form__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleExecute}
              disabled={working}
            >
              <Play size={16} aria-hidden="true" />
              {working ? 'Executing…' : 'Execute request (simulated)'}
            </button>
          </div>
        </>
      ) : (
        <div className="callout tone-warning" role="note">
          <AlertTriangle size={18} aria-hidden="true" />
          <p>One or more pre-execution checks did not pass. This request cannot be executed right now.</p>
        </div>
      )}
    </div>
  )
}

function VerifyForm({ execution, onVerified }) {
  const { role } = useDemoRole()
  const ids = useId()
  const [comment, setComment] = useState('')
  const [working, setWorking] = useState(null)
  const [error, setError] = useState(null)
  const [commentProblem, setCommentProblem] = useState('')

  if (!role.canApprove && role.id === execution.executedBy) {
    return (
      <div className="callout tone-neutral" role="note">
        <Info size={18} aria-hidden="true" />
        <p>You executed this request. A different demo role must verify it. Switch the demo role in the top bar.</p>
      </div>
    )
  }

  if (role.id === execution.executedBy) {
    return (
      <div className="callout tone-neutral" role="note">
        <Info size={18} aria-hidden="true" />
        <p>You executed this request as <strong>{role.label}</strong>. Switch to a different demo role to verify it.</p>
      </div>
    )
  }

  async function verify(decision) {
    if (working) return
    if (decision === 'DISPUTED' && !comment.trim()) {
      setCommentProblem('Add a comment explaining why the execution is disputed.')
      return
    }
    setCommentProblem('')
    setWorking(decision)
    setError(null)
    try {
      const result = await api.verifyExecution({
        executionId: execution.id,
        decision,
        comment,
        actorId: role.id,
      })
      onVerified(result)
    } catch (caught) {
      setError(caught)
      setWorking(null)
    }
  }

  return (
    <div className="form">
      <div className="callout tone-brand" role="note">
        <ShieldCheck size={18} aria-hidden="true" />
        <p>
          <strong>Independent verification.</strong> Compare the execution result with the original approved request before confirming or disputing.
        </p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={`${ids}-comment`}>
          Verification comment <span className="form__optional">(optional for verified, required for disputed)</span>
        </label>
        <textarea
          id={`${ids}-comment`}
          className={`input ${commentProblem ? 'is-invalid' : ''}`}
          rows={3}
          maxLength={TEXT_MAX}
          value={comment}
          onChange={(e) => { setComment(e.target.value); if (commentProblem) setCommentProblem('') }}
          aria-invalid={Boolean(commentProblem)}
          aria-describedby={`${ids}-comment-hint`}
          disabled={Boolean(working)}
        />
        <p id={`${ids}-comment-hint`} className={`form__hint ${commentProblem ? 'form__hint--error' : ''}`}>
          {commentProblem || 'Your comment is saved with the verification record.'}
        </p>
      </div>

      {error && (
        <div className="callout tone-danger" role="alert">
          <p><strong>Verification was not saved.</strong> {error.message}</p>
        </div>
      )}

      <div className="form__actions">
        <button type="button" className="btn btn--danger" onClick={() => verify('DISPUTED')} disabled={Boolean(working)}>
          <X size={16} aria-hidden="true" /> {working === 'DISPUTED' ? 'Disputing…' : 'Dispute'}
        </button>
        <button type="button" className="btn btn--success" onClick={() => verify('VERIFIED')} disabled={Boolean(working)}>
          <Check size={16} aria-hidden="true" /> {working === 'VERIFIED' ? 'Verifying…' : 'Verify'}
        </button>
      </div>
    </div>
  )
}

export default function ExecutionDetail({ request, executions, verifications, onExecuted, onVerified }) {
  const [localExecution, setLocalExecution] = useState(null)
  const [localVerification, setLocalVerification] = useState(null)

  // Find the latest execution for this request
  const existingExecution = executions.find((e) => e.requestId === request.id)
  const execution = localExecution ?? existingExecution
  const successfulExecution = execution?.status === 'SUCCESS'

  // Find the verification for this execution
  const existingVerification = execution
    ? verifications.find((v) => v.executionId === execution.id)
    : null
  const verification = localVerification ?? existingVerification

  const snapshot = request.snapshot ?? {}
  const classification = snapshot.classification ? getClassification(snapshot.classification) : null
  const severity = getSeverity(snapshot.severity)
  const status = getRequestStatus(request.status)

  function handleExecuted(exec) {
    setLocalExecution(exec)
    onExecuted(exec)
  }

  function handleVerified(result) {
    setLocalExecution(result.execution)
    setLocalVerification(result.verification)
    onVerified(result)
  }

  return (
    <div className="detail">
      <div className="detail__badges">
        <Badge tone={status.tone}>{status.label}</Badge>
        {execution && <Badge tone={getExecutionStatus(execution.status).tone}>{getExecutionStatus(execution.status).label}</Badge>}
        {execution && <Badge tone={getVerificationStatus(execution.verificationStatus).tone}>{getVerificationStatus(execution.verificationStatus).label}</Badge>}
      </div>

      {IS_DEMO && <p className="note tone-warning">Synthetic demo request. It does not describe a real person or account.</p>}

      {/* Request details */}
      <Section title="Approved request">
        <dl className="kv">
          <Fact label="Request ID"><code className="code-chip">{request.id}</code></Fact>
          <Fact label="Type">{getRequestType(request.requestType).label}</Fact>
          <Fact label="Reason">{request.reason ? <span className="prewrap">{request.reason}</span> : null}</Fact>
          <Fact label="Approved by">{request.decidedBy ? <code className="code-chip">{request.decidedBy}</code> : null}</Fact>
          <Fact label="Approved at">{request.decidedAt ? formatDateTime(request.decidedAt) : null}</Fact>
        </dl>
      </Section>

      {/* Snapshot at time of request */}
      <Section title="Finding snapshot" tag={{ kind: 'observed', label: 'At time of request' }}>
        <dl className="kv">
          <Fact label="Employee">{snapshot.employeeName}</Fact>
          <Fact label="Employee ID">{snapshot.employeeId}</Fact>
          <Fact label="Application">{snapshot.system}</Fact>
          <Fact label="Account">{snapshot.accountId ? <code className="code-chip">{snapshot.accountId}</code> : null}</Fact>
          <Fact label="Classification">{classification ? <Badge tone={classification.tone} icon={classification.icon}>{classification.label}</Badge> : null}</Fact>
          <Fact label="Severity">{severity ? <Badge tone={severity.tone}>{severity.label}</Badge> : null}</Fact>
        </dl>
        {request.findingId && (
          <p className="detail__link">
            <Link to={`/findings?finding=${encodeURIComponent(request.findingId)}`}>Open this finding</Link>
          </p>
        )}
      </Section>

      {/* Execution section */}
      <Section title="Execution">
        {execution ? (
          <>
            <dl className="kv">
              <Fact label="Execution ID"><code className="code-chip">{execution.id}</code></Fact>
              <Fact label="Result"><Badge tone={getExecutionStatus(execution.status).tone}>{getExecutionStatus(execution.status).label}</Badge></Fact>
              <Fact label="Executed by">{execution.executedBy ? <code className="code-chip">{execution.executedBy}</code> : null}</Fact>
              <Fact label="Executed at">{execution.executedAt ? formatDateTime(execution.executedAt) : null}</Fact>
              {execution.failureReason && <Fact label="Failure reason"><span className="prewrap tone-danger">{execution.failureReason}</span></Fact>}
            </dl>
            {execution.preChecks && (
              <details className="pre-checks-details">
                <summary>Pre-execution checks ({execution.preChecks.length})</summary>
                <PreChecksList checks={execution.preChecks} />
              </details>
            )}
          </>
        ) : (
          <ExecuteForm request={request} executions={executions} onExecuted={handleExecuted} />
        )}
      </Section>

      {/* Verification section */}
      <Section title="Verification">
        {!execution ? (
          <p className="detail__hint">Execute the request first. Verification is a separate step that happens after execution.</p>
        ) : execution.status === 'FAILED' ? (
          <p className="detail__hint">This execution failed. Only successful executions can be verified.</p>
        ) : verification ? (
          <dl className="kv">
            <Fact label="Verification ID"><code className="code-chip">{verification.id}</code></Fact>
            <Fact label="Decision"><Badge tone={getVerificationStatus(verification.decision).tone}>{getVerificationStatus(verification.decision).label}</Badge></Fact>
            <Fact label="Verified by">{verification.verifiedBy ? <code className="code-chip">{verification.verifiedBy}</code> : null}</Fact>
            <Fact label="Verified at">{verification.verifiedAt ? formatDateTime(verification.verifiedAt) : null}</Fact>
            <Fact label="Comment">{verification.comment ? <span className="prewrap">{verification.comment}</span> : <span className="muted">No comment was added.</span>}</Fact>
          </dl>
        ) : successfulExecution && execution.verificationStatus === 'UNVERIFIED' ? (
          <VerifyForm execution={execution} onVerified={handleVerified} />
        ) : (
          <p className="detail__hint">Verification is not available for this execution.</p>
        )}
      </Section>
    </div>
  )
}
