import { Activity, Check, FileText, Play, ShieldCheck, X, XCircle, AlertTriangle } from 'lucide-react'

// Event type names below are placeholders. Replace them with the real ones from docs/api.md.
const EVENT_META = {
  SCAN_COMPLETED: { label: 'Scan completed', icon: Activity, tone: 'brand' },
  REQUEST_PREPARED: { label: 'Request prepared', icon: FileText, tone: 'neutral' },
  REQUEST_APPROVED: { label: 'Request approved', icon: Check, tone: 'success' },
  REQUEST_REJECTED: { label: 'Request rejected', icon: X, tone: 'danger' },
  EXECUTION_COMPLETED: { label: 'Execution completed', icon: Play, tone: 'success' },
  EXECUTION_FAILED: { label: 'Execution failed', icon: XCircle, tone: 'danger' },
  EXECUTION_VERIFIED: { label: 'Execution verified', icon: ShieldCheck, tone: 'success' },
  EXECUTION_DISPUTED: { label: 'Execution disputed', icon: AlertTriangle, tone: 'warning' },
}

function humanize(type) {
  if (!type) return 'Unknown event'
  const text = String(type).replace(/_/g, ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function getEventMeta(type) {
  return EVENT_META[type] ?? { label: humanize(type), icon: Activity, tone: 'neutral' }
}

// Outcome shown on the Audit trail page. Derived from the recorded event type only; nothing is guessed.
const OUTCOME_BY_TYPE = {
  SCAN_COMPLETED: { key: 'COMPLETED', label: 'Completed', tone: 'brand' },
  REQUEST_PREPARED: { key: 'SUBMITTED', label: 'Submitted', tone: 'neutral' },
  REQUEST_APPROVED: { key: 'APPROVED', label: 'Approved', tone: 'success' },
  REQUEST_REJECTED: { key: 'REJECTED', label: 'Rejected', tone: 'danger' },
  EXECUTION_COMPLETED: { key: 'SUCCESS', label: 'Success', tone: 'success' },
  EXECUTION_FAILED: { key: 'FAILED', label: 'Failed', tone: 'danger' },
  EXECUTION_VERIFIED: { key: 'VERIFIED', label: 'Verified', tone: 'success' },
  EXECUTION_DISPUTED: { key: 'DISPUTED', label: 'Disputed', tone: 'warning' },
}

export function getEventOutcome(type) {
  return OUTCOME_BY_TYPE[type] ?? { key: 'UNKNOWN', label: 'Not recorded', tone: 'neutral' }
}

export function listOutcomes() {
  return Object.values(OUTCOME_BY_TYPE).map(({ key, label }) => ({ key, label }))
}

export function listEventTypes() {
  return Object.keys(EVENT_META).map((type) => ({ type, label: EVENT_META[type].label }))
}

// Spreadsheet programs can run a cell that starts with = + - or @ as a formula, so those get a leading apostrophe.
// Values containing commas, quotes or line breaks are wrapped in quotes with inner quotes doubled.
export function csvCell(value) {
  let text = value === null || value === undefined ? '' : String(value)
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function eventsToCsv(events) {
  const header = ['Timestamp', 'Event type', 'Outcome', 'Request reference', 'Reference', 'Actor', 'Details']
  const rows = events.map((event) => [
    event.timestamp, getEventMeta(event.type).label, getEventOutcome(event.type).label,
    event.requestId, event.subject, event.actor, event.details,
  ])
  return [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
}
