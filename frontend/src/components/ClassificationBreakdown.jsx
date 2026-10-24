import { CLASSIFICATION_ORDER, CLASSIFICATIONS } from '../utils/classifications.js'

export default function ClassificationBreakdown({ counts }) {
  const total = counts.total
  const rows = CLASSIFICATION_ORDER.map((key) => ({ key, ...CLASSIFICATIONS[key], count: counts[key] ?? 0 }))
  const summary = rows.map((row) => `${row.count} ${row.label}`).join(', ')

  return (
    <>
      <div className="bar" role="img" aria-label={`Classification breakdown: ${summary}`}>
        {rows.filter((row) => row.count > 0).map((row) => (
          <span key={row.key} className={`bar__seg tone-${row.tone}`} style={{ flexGrow: row.count }} />
        ))}
      </div>
      <ul className="legend">
        {rows.map((row) => (
          <li key={row.key} className={`legend__row tone-${row.tone}`}>
            <span className="legend__dot" aria-hidden="true" />
            <div>
              <p className="legend__name">{row.label} <code className="code-chip">{row.key}</code></p>
              <p className="legend__desc">{row.description}</p>
            </div>
            <span className="legend__count">{row.count}</span>
            <span className="legend__pct">{total ? Math.round((row.count / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </>
  )
}
