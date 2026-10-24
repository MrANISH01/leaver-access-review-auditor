import { Search, X } from 'lucide-react'
import { CLASSIFICATION_ORDER, CLASSIFICATIONS } from '../utils/classifications.js'
import { getReviewStatus } from '../utils/findingMeta.js'

export default function FindingsToolbar({
  disabled, counts, search, onSearch,
  classification, onClassification,
  system, systems, onSystem,
  status, statuses, onStatus,
  hasFilters, onClear,
}) {
  const chips = [
    { key: '', label: 'All', count: counts.total, tone: 'brand' },
    ...CLASSIFICATION_ORDER.map((key) => ({ key, label: CLASSIFICATIONS[key].label, count: counts[key], tone: CLASSIFICATIONS[key].tone })),
  ]

  return (
    <div className="toolbar">
      <div className="toolbar__row">
        <label className="search">
          <span className="sr-only">Search findings</span>
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            placeholder="Search name, employee ID, application or account"
            disabled={disabled}
          />
        </label>

        <label className="field">
          <span className="sr-only">Filter by application</span>
          <select value={system} onChange={(event) => onSystem(event.target.value)} disabled={disabled}>
            <option value="">All applications</option>
            {systems.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>

        {statuses.length > 0 && (
          <label className="field">
            <span className="sr-only">Filter by review status</span>
            <select value={status} onChange={(event) => onStatus(event.target.value)} disabled={disabled}>
              <option value="">All review statuses</option>
              {statuses.map((value) => <option key={value} value={value}>{getReviewStatus(value).label}</option>)}
            </select>
          </label>
        )}

        {hasFilters && (
          <button type="button" className="btn btn--secondary btn--small" onClick={onClear}>
            <X size={14} aria-hidden="true" /> Clear filters
          </button>
        )}
      </div>

      <div className="chips" role="group" aria-label="Filter by classification">
        {chips.map((chip) => {
          const active = classification === chip.key
          return (
            <button
              key={chip.key || 'all'}
              type="button"
              className={`chip tone-${chip.tone} ${active ? 'is-active' : ''}`}
              aria-pressed={active}
              onClick={() => onClassification(chip.key)}
              disabled={disabled}
            >
              {chip.label} <span className="chip__count">{chip.count}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
