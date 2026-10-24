// Display labels and rules for execution and verification.

export const EXECUTION_STATUSES = {
  PENDING: { label: 'Pending execution', tone: 'warning' },
  SUCCESS: { label: 'Executed successfully', tone: 'success' },
  FAILED: { label: 'Execution failed', tone: 'danger' },
}

export const VERIFICATION_STATUSES = {
  UNVERIFIED: { label: 'Not verified', tone: 'warning' },
  VERIFIED: { label: 'Verified', tone: 'success' },
  DISPUTED: { label: 'Disputed', tone: 'danger' },
}

function humanize(value) {
  const text = String(value).replace(/_/g, ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function getExecutionStatus(value) {
  if (!value) return { label: 'Not available', tone: 'neutral' }
  return EXECUTION_STATUSES[value] ?? { label: humanize(value), tone: 'neutral' }
}

export function getVerificationStatus(value) {
  if (!value) return { label: 'Not available', tone: 'neutral' }
  return VERIFICATION_STATUSES[value] ?? { label: humanize(value), tone: 'neutral' }
}

// Pre-execution checks: returns an array of { label, passed, reason } objects.
export function runPreExecutionChecks(request, existingExecutions) {
  const checks = []

  // 1. Approval status
  checks.push({
    label: 'Approval status',
    passed: request.status === 'APPROVED',
    reason: request.status === 'APPROVED'
      ? 'Request is approved.'
      : request.status === 'REJECTED'
        ? 'Request was rejected. Rejected requests cannot be executed.'
        : 'Request is still pending approval.',
  })

  // 2. Required information
  const snapshot = request.snapshot ?? {}
  const hasInfo = Boolean(snapshot.system && snapshot.accountId)
  checks.push({
    label: 'Required information',
    passed: hasInfo,
    reason: hasInfo
      ? 'System and account information is available.'
      : 'Missing required system or account information.',
  })

  // 3. Eligibility — request type must be actionable
  const actionable = ['DISABLE_ACCOUNT', 'CONFIRM_OWNERSHIP', 'DOCUMENT_EXCEPTION']
  checks.push({
    label: 'Eligibility',
    passed: actionable.includes(request.requestType),
    reason: actionable.includes(request.requestType)
      ? `Request type "${request.requestType}" is eligible for execution.`
      : 'This request type is not eligible for execution.',
  })

  // 4. Duplicate check
  const alreadyExecuted = existingExecutions.some(
    (exec) => exec.requestId === request.id && exec.status === 'SUCCESS'
  )
  checks.push({
    label: 'Duplicate check',
    passed: !alreadyExecuted,
    reason: alreadyExecuted
      ? 'This request has already been successfully executed. Duplicate execution is not allowed.'
      : 'No prior successful execution found for this request.',
  })

  return checks
}

// Whether all pre-execution checks pass
export function allChecksPassed(checks) {
  return checks.every((check) => check.passed)
}

// Gets the execution eligibility for a request (used for table display)
export function getExecutionEligibility(request, executions) {
  if (request.status !== 'APPROVED') {
    return { eligible: false, reason: 'Only approved requests can be executed.' }
  }
  const alreadyExecuted = executions.some(
    (exec) => exec.requestId === request.id && exec.status === 'SUCCESS'
  )
  if (alreadyExecuted) {
    return { eligible: false, reason: 'Already executed.', executed: true }
  }
  return { eligible: true, reason: '' }
}
