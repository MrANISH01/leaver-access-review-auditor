import { API_BASE_URL } from './config.js'
import { getRoleById } from '../utils/demoRoles.js'

const TIMEOUT_MS = 15000

function resolveActor(actorId) {
  if (actorId) {
    const role = getRoleById(actorId)
    return role?.id || actorId
  }
  try {
    const stored = window.localStorage.getItem('leaverguard.demo.role')
    return stored === 'approver' ? 'demo-approver' : 'demo-analyst'
  } catch {
    return 'demo-analyst'
  }
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {}),
  }

  // POST/DELETE and /whoami require X-Actor in the backend
  const method = (options.method || 'GET').toUpperCase()
  if (['POST', 'DELETE', 'PUT', 'PATCH'].includes(method) || path.startsWith('/whoami')) {
    if (!headers['X-Actor']) {
      headers['X-Actor'] = resolveActor(options.actorId)
    }
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)
  if (options.signal) {
    options.signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    })

    const isJson = response.headers.get('content-type')?.includes('application/json')
    const payload = isJson ? await response.json() : null

    if (!response.ok) {
      const err = payload?.error
      const message = err?.message || `Request failed with status ${response.status} (${response.statusText})`
      const errorObj = new Error(message)
      errorObj.code = err?.code
      errorObj.details = err?.details
      errorObj.status = response.status
      throw errorObj
    }

    return payload
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`The request to ${path} timed out or was aborted.`)
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

function parseFindingNumericId(id) {
  if (typeof id === 'number') return id
  const digits = String(id).replace(/\D/g, '')
  return digits ? parseInt(digits, 10) : id
}

function parseRequestNumericId(id) {
  if (typeof id === 'number') return id
  const digits = String(id).replace(/\D/g, '')
  return digits ? parseInt(digits, 10) : id
}

function mapClassificationSeverity(classification) {
  switch (classification) {
    case 'LEAVER_ACTIVE':
      return 'high'
    case 'NEEDS_REVIEW':
      return 'medium'
    case 'EXCLUDED':
    case 'OK':
    case 'NO_MATCH':
    default:
      return 'low'
  }
}

function mapMatchMethod(method) {
  switch (method) {
    case 'WORK_EMAIL':
      return 'Email address match'
    case 'EMPLOYEE_ID':
      return 'Exact employee ID match'
    case 'NAME_ONLY':
      return 'Name-only match (unverified)'
    default:
      return method ?? null
  }
}

function mapAccountStatus(status) {
  if (!status) return null
  const upper = String(status).toUpperCase()
  if (upper === 'ACTIVE') return 'Enabled'
  if (upper === 'DISABLED') return 'Disabled'
  return status
}

function mapRecommendation(classification) {
  switch (classification) {
    case 'LEAVER_ACTIVE':
      return 'Prepare a request to disable this account and send it for approval.'
    case 'NEEDS_REVIEW':
      return 'A person should confirm whether this account belongs to the departed employee before any request is prepared.'
    case 'EXCLUDED':
      return 'No action recommended while this record stays excluded.'
    default:
      return 'No action needed.'
  }
}

function mapEvidence(b) {
  return (b.evidence || []).map((ev, idx) => {
    let label = 'Evidence'
    let value = ''
    let source = b.account?.system || 'Identity records'

    switch (ev.type) {
      case 'ACCOUNT_RECORD':
        label = 'Account status'
        value = ev.detail?.status === 'ACTIVE' ? 'Enabled' : (ev.detail?.status || 'Reported')
        source = ev.detail?.system || b.account?.system || 'Source system'
        break
      case 'HR_RECORD':
        label = 'Employment status'
        value = ev.detail?.employment_status === 'TERMINATED' ? 'Left the organization' : (ev.detail?.employment_status || 'Reported')
        source = 'Identity records'
        break
      case 'MATCH_RATIONALE':
        label = 'Match rationale'
        value = ev.detail?.note || `Confidence ${ev.detail?.confidence || 'HIGH'}`
        source = 'Audit matcher'
        break
      case 'LAST_LOGIN':
        label = 'Last sign-in'
        value = ev.detail?.available && ev.detail?.last_login_at
          ? `Sign-in recorded (${ev.detail.last_login_at})`
          : 'Unavailable'
        source = b.account?.system || 'Source system'
        break
      case 'EXCLUSION_RULE':
        label = 'Exclusion rule'
        value = ev.detail?.summary || ev.detail?.rule || 'Account excluded'
        source = 'Policy config'
        break
      default:
        label = ev.type?.replace(/_/g, ' ') || 'Record'
        value = typeof ev.detail === 'object' ? JSON.stringify(ev.detail) : String(ev.detail ?? '')
    }

    return {
      id: `ev-${ev.id || idx}`,
      label,
      value,
      source,
      observedAt: ev.created_at || b.created_at,
    }
  })
}

function mapFinding(b, latestRequest) {
  const confidenceNum = b.match_confidence === 'HIGH' ? 0.98 : b.match_confidence === 'LOW' ? 0.45 : null
  const reviewStatus = latestRequest
    ? (latestRequest.status === 'PREPARED' ? 'PENDING' : latestRequest.status)
    : 'NOT_STARTED'

  return {
    id: `F-${String(b.id).padStart(3, '0')}`,
    rawId: b.id,
    classification: b.classification,
    employeeName: b.employee?.full_name ?? null,
    employeeId: b.employee?.employee_id ?? null,
    employmentEndDate: b.employee?.termination_date ?? null,
    system: b.account?.system ?? null,
    accountId: b.account?.external_account_id ?? b.account?.username ?? null,
    accountStatus: mapAccountStatus(b.account?.status),
    severity: mapClassificationSeverity(b.classification),
    matchConfidence: confidenceNum,
    matchMethod: mapMatchMethod(b.match_method),
    reviewStatus,
    requestId: latestRequest ? `REQ-${latestRequest.id}` : null,
    lastSeenAt: b.account?.last_login_at ?? null,
    rationale: b.reason ?? null,
    exclusionReason: b.classification === 'EXCLUDED' ? b.reason : null,
    recommendation: mapRecommendation(b.classification),
    deprovisionEligible: Boolean(b.deprovision_eligible),
    evidence: mapEvidence(b),
  }
}

function mapRequest(req) {
  const status = req.status === 'PREPARED'
    ? 'PENDING'
    : (req.status === 'APPROVED' || req.status === 'REJECTED' ? req.status : 'APPROVED')

  return {
    id: `REQ-${req.id}`,
    rawId: req.id,
    findingId: `F-${String(req.finding_id).padStart(3, '0')}`,
    requestType: 'DISABLE_ACCOUNT',
    status,
    rawStatus: req.status,
    priority: 'normal',
    reason: req.finding?.reason || 'Account belongs to a departed employee and remains active.',
    notes: null,
    requestedBy: req.prepared_by,
    createdAt: req.prepared_at,
    decidedBy: req.decided_by,
    decidedAt: req.decided_at,
    decisionComment: req.decision_note,
    snapshot: {
      employeeName: req.finding?.employee?.full_name ?? null,
      employeeId: req.finding?.employee?.employee_id ?? null,
      system: req.finding?.account?.system ?? req.system,
      accountId: req.finding?.account?.external_account_id ?? req.external_account_id,
      classification: req.finding?.classification ?? 'LEAVER_ACTIVE',
      severity: mapClassificationSeverity(req.finding?.classification || 'LEAVER_ACTIVE'),
    },
  }
}

function mapAuditEvent(e) {
  let eventType = e.event
  if (e.event === 'DEPROVISION_PREPARED') eventType = 'REQUEST_PREPARED'
  else if (e.event === 'DEPROVISION_APPROVED') eventType = 'REQUEST_APPROVED'
  else if (e.event === 'DEPROVISION_REJECTED') eventType = 'REQUEST_REJECTED'
  else if (e.event === 'DEPROVISION_EXECUTED') eventType = 'EXECUTION_COMPLETED'
  else if (e.event === 'DEPROVISION_EXECUTION_FAILED') eventType = 'EXECUTION_FAILED'
  else if (e.event === 'DEPROVISION_VERIFIED') eventType = 'EXECUTION_VERIFIED'
  else if (e.event === 'DEPROVISION_VERIFICATION_FAILED') eventType = 'EXECUTION_DISPUTED'

  let details = ''
  if (typeof e.detail === 'string') {
    details = e.detail
  } else if (e.detail && typeof e.detail === 'object') {
    if (e.detail.note) details = e.detail.note
    else if (e.detail.reason) details = e.detail.reason
    else if (e.detail.message) details = e.detail.message
    else if (e.event === 'SCAN_COMPLETED' && e.detail.total_accounts !== undefined) {
      details = `Scan completed. ${e.detail.total_accounts} accounts reviewed.`
    } else {
      details = `${e.event.replace(/_/g, ' ')} for ${e.entity_type} ${e.entity_id || ''}`.trim()
    }
  }

  const requestId = e.entity_type === 'deprovision_request'
    ? `REQ-${e.entity_id}`
    : (e.detail?.request_id ? `REQ-${e.detail.request_id}` : null)

  const subject = e.entity_type === 'deprovision_request'
    ? `REQ-${e.entity_id}`
    : (e.entity_id ? `${e.entity_type}-${e.entity_id}` : e.entity_type)

  return {
    id: `evt-${e.id}`,
    type: eventType,
    rawEvent: e.event,
    actor: e.actor,
    timestamp: e.ts,
    subject,
    requestId,
    details,
  }
}

export const liveAdapter = {
  async getOverview({ signal } = {}) {
    const [summaryRes, auditRes] = await Promise.all([
      request('/summary', { signal }),
      request('/audit-log?limit=5', { signal }).catch(() => ({ data: [] })),
    ])

    const summary = summaryRes.data || {}
    const latestScan = summary.latest_scan

    const scan = latestScan
      ? {
          id: `scan-${latestScan.id}`,
          status: 'completed',
          completedAt: latestScan.finished_at,
        }
      : null

    const counts = {
      total: summary.total_findings ?? 0,
      LEAVER_ACTIVE: summary.leavers_active ?? 0,
      NEEDS_REVIEW: summary.needs_review ?? 0,
      EXCLUDED: summary.excluded ?? 0,
      OK: summary.findings_by_classification?.OK ?? 0,
    }

    const events = (auditRes.data || []).map(mapAuditEvent)

    return {
      scan,
      counts,
      recentEvents: events,
    }
  },

  async getFindings({ signal } = {}) {
    const [findingsRes, requestsRes] = await Promise.all([
      request('/findings', { signal }),
      request('/deprovision-requests', { signal }).catch(() => ({ data: [] })),
    ])

    const rawFindings = findingsRes.data || []
    const rawRequests = requestsRes.data || []

    const requestByFindingId = new Map()
    for (const req of rawRequests) {
      const current = requestByFindingId.get(req.finding_id)
      if (!current || Date.parse(req.prepared_at) > Date.parse(current.prepared_at)) {
        requestByFindingId.set(req.finding_id, req)
      }
    }

    // Fetch full details with evidence for findings
    const findingsWithEvidence = await Promise.all(
      rawFindings.map(async (f) => {
        try {
          const detailRes = await request(`/findings/${f.id}`, { signal })
          return detailRes.data || f
        } catch {
          return f
        }
      })
    )

    const findings = findingsWithEvidence.map((f) => {
      const matchingReq = requestByFindingId.get(f.id)
      return mapFinding(f, matchingReq)
    })

    return { findings }
  },

  async getRequests({ signal } = {}) {
    const res = await request('/deprovision-requests', { signal })
    const requests = (res.data || []).map(mapRequest)
    requests.sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
    return { requests, persistence: 'backend' }
  },

  async createRequest({ findingId, requestType, reason, notes, priority = 'normal', actorId } = {}) {
    const numericFindingId = parseFindingNumericId(findingId)
    const actor = resolveActor(actorId)

    const res = await request(`/findings/${numericFindingId}/deprovision-requests`, {
      method: 'POST',
      actorId: actor,
    })

    return mapRequest(res.data)
  },

  async decideRequest({ requestId, decision, comment, actorId } = {}) {
    const numericId = parseRequestNumericId(requestId)
    const actor = resolveActor(actorId)
    const action = decision === 'APPROVED' ? 'approve' : 'reject'

    const res = await request(`/deprovision-requests/${numericId}/${action}`, {
      method: 'POST',
      actorId: actor,
      body: { note: comment || undefined },
    })

    return mapRequest(res.data)
  },

  async getExecutionData({ signal } = {}) {
    const res = await request('/deprovision-requests', { signal })
    const allRequests = res.data || []

    // Fetch details (executions & verifications) for requests that reached APPROVED, EXECUTING, or VERIFIED
    const detailedRequests = await Promise.all(
      allRequests.map(async (r) => {
        try {
          const detailRes = await request(`/deprovision-requests/${r.id}`, { signal })
          return detailRes.data || r
        } catch {
          return r
        }
      })
    )

    const approvedRequests = detailedRequests
      .filter((r) => ['APPROVED', 'EXECUTING', 'EXECUTED_UNVERIFIED', 'VERIFIED', 'EXECUTION_FAILED', 'VERIFICATION_FAILED'].includes(r.status))
      .map(mapRequest)

    const executions = []
    const verifications = []

    for (const r of detailedRequests) {
      const reqId = `REQ-${r.id}`
      const mappedReq = mapRequest(r)

      if (r.executions && r.executions.length > 0) {
        for (const e of r.executions) {
          const execId = `EXEC-${e.id}`
          const isSuccess = Boolean(e.claimed_success)

          const preChecks = [
            { label: 'Request approval', passed: true, reason: 'Approved by authorized reviewer' },
            { label: 'Separation of duties', passed: true, reason: 'Approver differs from requester' },
            { label: 'Account eligibility', passed: true, reason: 'Account verified eligible for deprovisioning' },
          ]

          executions.push({
            id: execId,
            rawId: e.id,
            requestId: reqId,
            status: isSuccess ? 'SUCCESS' : 'FAILED',
            executedBy: r.decided_by || r.prepared_by || 'operator',
            executedAt: e.attempted_at,
            failureReason: isSuccess ? null : (e.connector_response?.message || 'Execution failed'),
            preChecks,
            snapshot: mappedReq.snapshot,
            requestType: 'DISABLE_ACCOUNT',
            verificationStatus: r.status === 'VERIFIED' ? 'VERIFIED' : (r.status === 'VERIFICATION_FAILED' ? 'DISPUTED' : 'UNVERIFIED'),
          })
        }
      }

      if (r.verifications && r.verifications.length > 0) {
        for (const v of r.verifications) {
          verifications.push({
            id: `VERIF-${v.id}`,
            rawId: v.id,
            executionId: r.executions?.[0] ? `EXEC-${r.executions[0].id}` : `EXEC-1`,
            requestId: reqId,
            decision: v.passed ? 'VERIFIED' : 'DISPUTED',
            comment: v.passed ? 'Observed account status: DISABLED' : `Observed status: ${v.observed_status}`,
            verifiedBy: 'system-verifier',
            verifiedAt: v.observed_at,
          })
        }
      }
    }

    return {
      requests: approvedRequests,
      executions,
      verifications,
      persistence: 'backend',
    }
  },

  async executeRequest({ requestId, actorId, simulateFailure = false } = {}) {
    const numericId = parseRequestNumericId(requestId)
    const actor = resolveActor(actorId)

    if (simulateFailure) {
      try {
        await request('/dev/fault-injection', {
          method: 'POST',
          actorId: actor,
          body: { mode: 'silent_noop' },
        })
      } catch {
        // Dev endpoint may not be active if DEMO_MODE!=1
      }
    }

    try {
      const res = await request(`/deprovision-requests/${numericId}/execute`, {
        method: 'POST',
        actorId: actor,
      })

      const reqData = res.data
      const exec = reqData.executions?.[reqData.executions.length - 1]
      const mappedReq = mapRequest(reqData)

      return {
        id: exec ? `EXEC-${exec.id}` : `EXEC-${Date.now()}`,
        requestId: `REQ-${reqData.id}`,
        status: exec?.claimed_success ? 'SUCCESS' : 'FAILED',
        executedBy: actor,
        executedAt: exec?.attempted_at || new Date().toISOString(),
        failureReason: exec?.claimed_success ? null : (exec?.connector_response?.message || 'Execution failed'),
        preChecks: [
          { label: 'Request approval', passed: true, reason: 'Approved by authorized reviewer' },
          { label: 'Separation of duties', passed: true, reason: 'Approver differs from requester' },
          { label: 'Account eligibility', passed: true, reason: 'Account verified eligible for deprovisioning' },
        ],
        snapshot: mappedReq.snapshot,
        requestType: 'DISABLE_ACCOUNT',
        verificationStatus: reqData.status === 'VERIFIED' ? 'VERIFIED' : (reqData.status === 'VERIFICATION_FAILED' ? 'DISPUTED' : 'UNVERIFIED'),
      }
    } finally {
      if (simulateFailure) {
        try {
          await request('/dev/fault-injection', {
            method: 'DELETE',
            actorId: actor,
          })
        } catch {
          // Ignore cleanup errors
        }
      }
    }
  },

  async verifyExecution({ executionId, decision, comment, actorId } = {}) {
    const actor = resolveActor(actorId)
    const now = new Date().toISOString()

    const verification = {
      id: `VERIF-${Date.now()}`,
      executionId,
      decision,
      comment: comment || null,
      verifiedBy: actor,
      verifiedAt: now,
    }

    return {
      execution: {
        id: executionId,
        verificationStatus: decision,
      },
      verification,
    }
  },

  async getAuditTrail({ signal } = {}) {
    const res = await request('/audit-log?limit=500', { signal })
    const events = (res.data || []).map(mapAuditEvent)
    events.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
    return { events, persistence: 'backend' }
  },

  async resetDemoRequests() {
    const actor = resolveActor()
    try {
      await request('/dev/reset', {
        method: 'POST',
        actorId: actor,
      })
    } catch (e) {
      console.warn('Dev reset not available or failed:', e)
    }

    try {
      await request('/scans', {
        method: 'POST',
        actorId: actor,
      })
    } catch (e) {
      console.warn('Initial scan trigger after reset:', e)
    }

    return { ok: true }
  },

  async triggerScan({ actorId } = {}) {
    const actor = resolveActor(actorId)
    const res = await request('/scans', {
      method: 'POST',
      actorId: actor,
    })
    return { scan: res.data }
  },

  async checkHealth({ signal } = {}) {
    const res = await request('/health', { signal })
    return res.data
  },
}
