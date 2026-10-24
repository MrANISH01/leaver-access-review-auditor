import { FlaskConical } from 'lucide-react'
import { IS_DEMO } from '../services/config.js'

export default function DemoBanner() {
  if (!IS_DEMO) return null
  return (
    <div className="demo-banner" role="note">
      <FlaskConical size={16} aria-hidden="true" />
      <p>
        <strong>Demo mode.</strong> Everything on screen is synthetic. No real accounts have been scanned, changed or disabled.
      </p>
    </div>
  )
}
