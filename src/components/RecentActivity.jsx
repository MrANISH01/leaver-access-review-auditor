import { Activity } from 'lucide-react'
import { EmptyState } from './States.jsx'
import { getEventMeta } from '../utils/auditEvents.js'
import { formatDateTime, formatRelative } from '../utils/format.js'

export default function RecentActivity({ events }) {
  if (!events.length) {
    return <EmptyState icon={Activity} title="No audit events yet" text="Events appear here after a scan runs or a request is reviewed." />
  }

  return (
    <ul className="activity">
      {events.map((event) => {
        const meta = getEventMeta(event.type)
        const Icon = meta.icon
        return (
          <li key={event.id} className="activity__item">
            <span className={`activity__icon tone-${meta.tone}`}><Icon size={18} aria-hidden="true" /></span>
            <div>
              <p className="activity__title">
                {meta.label} {event.subject && <code className="code-chip">{event.subject}</code>}
              </p>
              <p className="activity__meta">
                {event.details || 'No details recorded.'} Recorded by <code className="code-chip">{event.actor || 'unknown actor'}</code>
              </p>
            </div>
            <time className="activity__time" dateTime={event.timestamp} title={formatDateTime(event.timestamp)}>
              {formatRelative(event.timestamp)}
            </time>
          </li>
        )
      })}
    </ul>
  )
}
