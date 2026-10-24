import { CLASSIFICATION_ORDER, getClassification } from './classifications.js'
import { getReviewStatus, getSeverity } from './findingMeta.js'

export const PAGE_SIZE = 10

// Sortable columns, in the order they appear in the table.
// value() returns a string or number, or null when the finding has no value.
// Missing values always sort last, whichever direction is chosen.
export const SORT_COLUMNS = {
  identity: { label: 'Identity', defaultDir: 'asc', value: (f) => f.employeeName?.toLowerCase() ?? null },
  system: { label: 'Application', defaultDir: 'asc', value: (f) => f.system?.toLowerCase() ?? null },
  account: { label: 'Account', defaultDir: 'asc', value: (f) => f.accountId?.toLowerCase() ?? null },
  classification: {
    label: 'Classification',
    defaultDir: 'asc',
    value: (f) => {
      const index = CLASSIFICATION_ORDER.indexOf(f.classification)
      return index === -1 ? null : index
    },
  },
  severity: { label: 'Severity', defaultDir: 'desc', value: (f) => getSeverity(f.severity)?.rank ?? null },
  confidence: {
    label: 'Match confidence',
    defaultDir: 'desc',
    value: (f) => (typeof f.matchConfidence === 'number' ? f.matchConfidence : null),
  },
  status: { label: 'Review status', defaultDir: 'asc', value: (f) => getReviewStatus(f.reviewStatus)?.label.toLowerCase() ?? null },
  lastSeen: {
    label: 'Last seen',
    defaultDir: 'desc',
    value: (f) => {
      const time = Date.parse(f.lastSeenAt)
      return Number.isNaN(time) ? null : time
    },
  },
}

export const DEFAULT_SORT = { key: 'classification', dir: 'asc' }

function compare(a, b, dir) {
  if (a === null && b === null) return 0
  if (a === null) return 1
  if (b === null) return -1
  const result = typeof a === 'string' ? a.localeCompare(b) : a - b
  return dir === 'desc' ? -result : result
}

export function sortFindings(findings, { key, dir }) {
  const column = SORT_COLUMNS[key] ?? SORT_COLUMNS[DEFAULT_SORT.key]
  const direction = SORT_COLUMNS[key] ? dir : DEFAULT_SORT.dir
  const { severity, identity, account } = SORT_COLUMNS
  // Ties fall back to severity (high first), then name, then account, so the order is stable.
  return [...findings].sort(
    (a, b) =>
      compare(column.value(a), column.value(b), direction) ||
      compare(severity.value(a), severity.value(b), 'desc') ||
      compare(identity.value(a), identity.value(b), 'asc') ||
      compare(account.value(a), account.value(b), 'asc'),
  )
}

export function filterFindings(findings, { q = '', classification = '', system = '', status = '' }) {
  const needle = q.trim().toLowerCase()
  return findings.filter((f) => {
    if (classification && f.classification !== classification) return false
    if (system && f.system !== system) return false
    if (status && f.reviewStatus !== status) return false
    if (needle) {
      const haystack = [f.employeeName, f.employeeId, f.system, f.accountId, getClassification(f.classification).label]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(needle)) return false
    }
    return true
  })
}

export function paginate(items, page, pageSize = PAGE_SIZE) {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize))
  const current = Math.min(Math.max(1, page), pageCount)
  const start = (current - 1) * pageSize
  const end = Math.min(start + pageSize, items.length)
  return { page: current, pageCount, start, end, total: items.length, items: items.slice(start, end) }
}

export function countByClassification(findings) {
  const counts = { total: findings.length }
  for (const key of CLASSIFICATION_ORDER) counts[key] = 0
  for (const f of findings) {
    if (f.classification in counts) counts[f.classification] += 1
  }
  return counts
}

export function distinctValues(findings, pick) {
  return [...new Set(findings.map(pick).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)))
}

// Reads the filters, sorting, page and open finding from the address bar (?classification=OK&sort=severity).
// Anything unrecognised is ignored, so a mistyped link can never break the page.
export function readQuery(params) {
  const classification = params.get('classification')
  const sortParam = params.get('sort')
  const dirParam = params.get('dir')
  const page = Number.parseInt(params.get('page') ?? '1', 10)
  const sortKey = SORT_COLUMNS[sortParam] ? sortParam : DEFAULT_SORT.key
  return {
    classification: CLASSIFICATION_ORDER.includes(classification) ? classification : '',
    system: params.get('system') ?? '',
    status: params.get('status') ?? '',
    sortKey,
    sortDir: dirParam === 'asc' || dirParam === 'desc' ? dirParam : SORT_COLUMNS[sortKey].defaultDir,
    page: Number.isFinite(page) && page > 0 ? page : 1,
    selectedId: params.get('finding') ?? '',
  }
}
