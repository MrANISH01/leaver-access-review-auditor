import { Inbox, RefreshCw, TriangleAlert } from 'lucide-react'

export function Skeleton({ width = '100%', height = 16 }) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />
}

export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="state">
      <span className="state__icon tone-neutral"><Icon size={22} aria-hidden="true" /></span>
      <h2>{title}</h2>
      {text && <p>{text}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state" role="alert">
      <span className="state__icon tone-danger"><TriangleAlert size={22} aria-hidden="true" /></span>
      <h2>We could not load this data</h2>
      <p>{error?.message || 'Something went wrong while loading.'}</p>
      {onRetry && (
        <button type="button" className="btn btn--secondary" onClick={onRetry}>
          <RefreshCw size={16} aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  )
}
