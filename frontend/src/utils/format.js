const NOT_AVAILABLE = 'Not available'

const dateTimeFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
})
const relativeFormat = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

// Note for Milestone 6: SQLite timestamps without a "Z" or offset are read as local time.
// Check the real format in docs/api.md and normalise it in the service layer.
function toDate(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTime(value) {
  const date = toDate(value)
  return date ? dateTimeFormat.format(date) : NOT_AVAILABLE
}

export function formatRelative(value) {
  const date = toDate(value)
  if (!date) return NOT_AVAILABLE
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const units = [['day', 86400], ['hour', 3600], ['minute', 60]]
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relativeFormat.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}
