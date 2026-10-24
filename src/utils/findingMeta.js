// Display labels for finding fields. Unknown values fall back to a readable version of the raw text.
function humanize(value) {
  const text = String(value).replace(/_/g, ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const SEVERITIES = {
  high: { label: 'High', tone: 'danger', rank: 3 },
  medium: { label: 'Medium', tone: 'warning', rank: 2 },
  low: { label: 'Low', tone: 'neutral', rank: 1 },
}

export function getSeverity(value) {
  if (!value) return null
  return SEVERITIES[String(value).toLowerCase()] ?? { label: humanize(value), tone: 'neutral', rank: 0 }
}

// Placeholder status names. Replace them with the real ones from docs/api.md.
// "Approved" is a decision only; it does not mean an account has been disabled.
export const REVIEW_STATUSES = {
  NOT_STARTED: { label: 'Not started', tone: 'neutral' },
  REQUEST_PREPARED: { label: 'Request prepared', tone: 'brand' },
  PENDING: { label: 'Pending approval', tone: 'warning' },
  APPROVED: { label: 'Approved', tone: 'success' },
  REJECTED: { label: 'Rejected', tone: 'danger' },
}

export function getReviewStatus(value) {
  if (!value) return null
  return REVIEW_STATUSES[value] ?? { label: humanize(value), tone: 'neutral' }
}
