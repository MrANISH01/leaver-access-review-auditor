// Display labels and rules for requests. Status and type names are frontend labels;
// confirm them against the backend API documentation when the live adapter is built.
export const REQUEST_TYPES = {
  DISABLE_ACCOUNT: {
    label: 'Disable account',
    description: 'Ask for the account to be disabled. Accounts are only ever disabled, never deleted.',
  },
  CONFIRM_OWNERSHIP: {
    label: 'Confirm account ownership',
    description: 'Ask the system owner or manager to confirm who actually uses this account.',
  },
  DOCUMENT_EXCEPTION: {
    label: 'Document an exception',
    description: 'Record why this account should stay active, for example during a handover period.',
  },
}

export const REQUEST_STATUSES = {
  PENDING: { label: 'Pending', tone: 'warning' },
  APPROVED: { label: 'Approved', tone: 'success' },
  REJECTED: { label: 'Rejected', tone: 'danger' },
}

export const PRIORITIES = {
  normal: { label: 'Normal', tone: 'neutral' },
  urgent: { label: 'Urgent', tone: 'danger' },
}

export const STATUS_ORDER = ['PENDING', 'APPROVED', 'REJECTED']
export const REASON_MIN = 10
export const TEXT_MAX = 500

function humanize(value) {
  const text = String(value).replace(/_/g, ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function getRequestType(value) {
  if (!value) return { label: 'Not available', description: '' }
  return REQUEST_TYPES[value] ?? { label: humanize(value), description: '' }
}

export function getRequestStatus(value) {
  if (!value) return { label: 'Not available', tone: 'neutral' }
  return REQUEST_STATUSES[value] ?? { label: humanize(value), tone: 'neutral' }
}

export function getPriority(value) {
  if (!value) return null
  return PRIORITIES[value] ?? { label: humanize(value), tone: 'neutral' }
}

// Only these classifications can start a request. OK and Excluded findings have nothing to remediate.
const REQUESTABLE = ['LEAVER_ACTIVE', 'NEEDS_REVIEW']

export function defaultRequestType(classification) {
  return classification === 'NEEDS_REVIEW' ? 'CONFIRM_OWNERSHIP' : 'DISABLE_ACCOUNT'
}

// Decides whether a request may be started from a finding. The finding must already carry
// the latest request status (the mock adapter adds it), so no second lookup is needed.
export function getRequestEligibility(finding) {
  if (!finding) return { allowed: false, reason: 'Finding not found.' }
  if (!REQUESTABLE.includes(finding.classification)) {
    return { allowed: false, reason: 'Requests can only be started for findings classified as "Leaver, still active" or "Needs review".' }
  }
  if (finding.reviewStatus === 'PENDING') {
    return { allowed: false, requestId: finding.requestId, reason: 'A request for this finding is already waiting for a decision.' }
  }
  if (finding.reviewStatus === 'APPROVED') {
    return { allowed: false, requestId: finding.requestId, reason: 'A request for this finding was already approved. Go to Execution and verification to carry it out.' }
  }
  return { allowed: true, reason: '' }
}
