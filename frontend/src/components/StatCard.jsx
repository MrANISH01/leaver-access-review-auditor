import { Link } from 'react-router-dom'
import { Skeleton } from './States.jsx'

export default function StatCard({ label, value, icon: Icon, tone = 'neutral', to, loading, emphasis }) {
  const className = `card stat tone-${tone} ${to ? 'stat--link' : ''} ${emphasis ? 'stat--emphasis' : ''}`
  const body = (
    <>
      <span className="stat__top">
        <span className="stat__label">{label}</span>
        <span className="stat__icon"><Icon size={18} aria-hidden="true" /></span>
      </span>
      <span className="stat__value">
        {loading ? <Skeleton width={56} height={30} /> : value ?? <span aria-label="Not available">—</span>}
      </span>
    </>
  )
  return to ? <Link to={to} className={className}>{body}</Link> : <div className={className}>{body}</div>
}
