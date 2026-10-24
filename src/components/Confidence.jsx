import NotAvailable from './NotAvailable.jsx'

// value is a fraction from 0 to 1. The bar is a single colour on purpose:
// we do not claim any threshold means "good" or "bad".
export default function Confidence({ value }) {
  if (typeof value !== 'number' || Number.isNaN(value)) return <NotAvailable />
  const percent = Math.round(Math.min(1, Math.max(0, value)) * 100)
  return (
    <span className="confidence" title={`Identity-match confidence: ${percent}%`}>
      <span className="confidence__bar" aria-hidden="true"><span style={{ width: `${percent}%` }} /></span>
      <span className="confidence__value">{percent}%</span>
    </span>
  )
}
