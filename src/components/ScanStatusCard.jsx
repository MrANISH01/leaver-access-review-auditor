import { Info } from 'lucide-react'
import Badge from './Badge.jsx'
import { formatDateTime, formatRelative } from '../utils/format.js'
import { IS_DEMO } from '../services/config.js'

const STATUS = {
  completed: { label: 'Completed', tone: 'success' },
  running: { label: 'Running', tone: 'brand' },
  failed: { label: 'Failed', tone: 'danger' },
}

export default function ScanStatusCard({ scan }) {
  const status = scan?.status ? STATUS[scan.status] ?? { label: scan.status, tone: 'neutral' } : null

  return (
    <>
      <dl className="facts">
        <div>
          <dt>Status</dt>
          <dd>{status ? <Badge tone={status.tone}>{status.label}</Badge> : 'Not available'}</dd>
        </div>
        <div>
          <dt>Last completed</dt>
          <dd>
            {formatDateTime(scan?.completedAt)}
            {scan?.completedAt && <small>{formatRelative(scan.completedAt)}</small>}
          </dd>
        </div>
        <div>
          <dt>Data source</dt>
          <dd>{IS_DEMO ? 'Synthetic demo data' : 'Backend API'}</dd>
        </div>
      </dl>
      <p className="note tone-brand">
        <Info size={16} aria-hidden="true" />
        Scans are read-only. They review accounts but never change them.
      </p>
    </>
  )
}
