import { FlaskConical, Radio } from 'lucide-react'
import { IS_DEMO } from '../services/config.js'

// Shows which data source the app is using. This is the mode that was selected,
// not proof that the backend is reachable (the System status page covers that).
export default function ModeBadge() {
  if (IS_DEMO) {
    return (
      <span className="pill tone-warning" title="All data comes from the built-in synthetic dataset.">
        <FlaskConical size={13} aria-hidden="true" /> Demo data
      </span>
    )
  }
  return (
    <span className="pill tone-brand" title="Data is requested from the backend API.">
      <Radio size={13} aria-hidden="true" /> Live mode
    </span>
  )
}
