import { Link } from 'react-router-dom'
import { FilePlus, Info } from 'lucide-react'
import { getRequestEligibility } from '../utils/requestMeta.js'

// Sits at the bottom of the evidence drawer. Starting a request only records a request for approval.
export default function FindingRequestAction({ finding, onStart }) {
  const eligibility = getRequestEligibility(finding)

  if (eligibility.allowed) {
    return (
      <div className="drawer__action">
        <p>
          {finding.reviewStatus === 'REJECTED'
            ? 'The previous request was rejected. You can start a new one.'
            : 'Start a request to have this finding reviewed and approved.'}
        </p>
        <button type="button" className="btn btn--primary" onClick={onStart}>
          <FilePlus size={16} aria-hidden="true" /> Start request
        </button>
      </div>
    )
  }

  return (
    <div className="drawer__action">
      <p className="drawer__action-note"><Info size={15} aria-hidden="true" /> {eligibility.reason}</p>
      {eligibility.requestId && (
        <Link to={`/requests?request=${encodeURIComponent(eligibility.requestId)}`} className="btn btn--secondary">
          View request
        </Link>
      )}
    </div>
  )
}
