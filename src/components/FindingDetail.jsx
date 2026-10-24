import { Eye } from 'lucide-react'
import Badge from './Badge.jsx'
import Confidence from './Confidence.jsx'
import NotAvailable from './NotAvailable.jsx'
import { IS_DEMO } from '../services/config.js'
import { getClassification } from '../utils/classifications.js'
import { getReviewStatus, getSeverity } from '../utils/findingMeta.js'
import { formatDateTime } from '../utils/format.js'

const TAGS = { observed: 'Observed', inferred: 'Inferred', recommended: 'Recommendation' }

// The tag tells the reader what kind of statement they are looking at:
// Observed = reported by a source system, Inferred = a conclusion drawn by the audit,
// Recommendation = a suggestion for a person to act on.
function Section({ title, kind, hint, children }) {
  return (
    <section className="detail__section">
      <div className="detail__head">
        <h3>{title}</h3>
        <span className={`tag tag--${kind}`}>{TAGS[kind]}</span>
      </div>
      <p className="detail__hint">{hint}</p>
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

export default function FindingDetail({ finding }) {
  const classification = getClassification(finding.classification)
  const severity = getSeverity(finding.severity)
  const status = getReviewStatus(finding.reviewStatus)
  const evidence = finding.evidence ?? []

  return (
    <div className="detail">
      <div className="detail__badges">
        <Badge tone={classification.tone} icon={classification.icon}>{classification.label}</Badge>
        {severity && <Badge tone={severity.tone}>{severity.label} severity</Badge>}
        {status && <Badge tone={status.tone}>Review: {status.label}</Badge>}
      </div>

      {IS_DEMO && (
        <p className="note tone-warning">Synthetic demo record. It does not describe a real person or account.</p>
      )}

      {finding.classification === 'NEEDS_REVIEW' && (
        <div className="callout tone-warning" role="note">
          <Eye size={18} aria-hidden="true" />
          <p>
            <strong>A person must investigate this finding.</strong> The audit could not confirm the identity match,
            so this account must not be treated as a confirmed leaver account.
          </p>
        </div>
      )}

      <Section title="What was detected" kind="observed" hint="Facts reported by the source systems.">
        <dl className="kv">
          <Fact label="Employee">{finding.employeeName}</Fact>
          <Fact label="Employee ID">{finding.employeeId}</Fact>
          <Fact label="Employment end date">{finding.employmentEndDate ? formatDateTime(finding.employmentEndDate) : null}</Fact>
          <Fact label="Application">{finding.system}</Fact>
          <Fact label="Account">{finding.accountId ? <code className="code-chip">{finding.accountId}</code> : null}</Fact>
          <Fact label="Account status">{finding.accountStatus}</Fact>
          <Fact label="Last seen">{finding.lastSeenAt ? formatDateTime(finding.lastSeenAt) : null}</Fact>
          <Fact label="Related request">{finding.requestId ? <code className="code-chip">{finding.requestId}</code> : null}</Fact>
        </dl>
      </Section>

      <Section title="Why it was classified this way" kind="inferred" hint="The audit's conclusion. It is drawn from the evidence, not observed directly.">
        <p className="detail__meaning">
          <strong>{classification.label}:</strong> {classification.description}
        </p>
        <p className="quote">{finding.rationale || <NotAvailable />}</p>
        {finding.classification === 'EXCLUDED' && (
          <dl className="kv">
            <Fact label="Exclusion reason">{finding.exclusionReason || 'The audit did not supply a reason.'}</Fact>
          </dl>
        )}
      </Section>

      <Section title="Identity match" kind="inferred" hint="How the audit linked this account to a person.">
        <dl className="kv">
          <Fact label="Confidence">{typeof finding.matchConfidence === 'number' ? <Confidence value={finding.matchConfidence} /> : null}</Fact>
          <Fact label="Method">{finding.matchMethod}</Fact>
        </dl>
      </Section>

      <Section title="Supporting evidence" kind="observed" hint="Individual records the classification is based on.">
        {evidence.length === 0 ? (
          <p className="quote"><NotAvailable /> No supporting evidence was supplied.</p>
        ) : (
          <ul className="evidence">
            {evidence.map((item) => (
              <li key={item.id}>
                <div>
                  <p className="evidence__label">{item.label || 'Evidence'}</p>
                  <p className="evidence__value">{item.value || <NotAvailable />}</p>
                </div>
                <div className="evidence__meta">
                  <p>Source: {item.source || 'not available'}</p>
                  {item.observedAt && <p>Observed {formatDateTime(item.observedAt)}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Recommended next step" kind="recommended" hint="Advice for a person to act on. Viewing a finding does not change any account.">
        <p className="quote">{finding.recommendation || <NotAvailable />}</p>
      </Section>
    </div>
  )
}
