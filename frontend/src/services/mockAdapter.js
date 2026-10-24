import { MOCK_AUDIT_EVENTS, MOCK_COUNTS, MOCK_FINDINGS, MOCK_SCAN } from '../data/mockData.js'
import { MOCK_SCENARIO } from './config.js'
import { loadState, nextRequestId, persistenceMode, resetState, saveState } from './requestStore.js'
import { loadExecutionState, saveExecutionState, resetExecutionState, executionPersistenceMode, nextExecutionId, nextVerificationId, addRequestEvent } from './executionStore.js'
import { PRIORITIES, REASON_MIN, REQUEST_TYPES, TEXT_MAX, getRequestEligibility, getRequestType } from '../utils/requestMeta.js'
import { runPreExecutionChecks, allChecksPassed } from '../utils/executionMeta.js'
import { getRoleById } from '../utils/demoRoles.js'

const LATENCY_MS = 450
const SLOW_LATENCY_MS = 3000
const SAVE_LATENCY_MS = 400

function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }, { once: true })
  })
}

// Shape the pages expect from getOverview():
// {
//   scan: { status, completedAt } | null,
//   counts: { total, LEAVER_ACTIVE, NEEDS_REVIEW, EXCLUDED, OK },
//   recentEvents: [{ id, type, actor, timestamp, subject, details }],
// }
//
// Shape the pages expect from getFindings():
// { findings: [Finding] }
// Finding = {
//   id, classification,                      always present
//   employeeName, employeeId,                string | null
//   employmentEndDate, lastSeenAt,           ISO date string | null
//   system, accountId, accountStatus,        string | null
//   severity,                                'high' | 'medium' | 'low' | null
//   matchConfidence,                         number from 0 to 1 | null
//   matchMethod,                             string | null
//   reviewStatus, requestId,                 string | null
//   rationale, exclusionReason,              string | null
//   recommendation,                          string | null
//   evidence: [{ id, label, value, source, observedAt }],
// }
//
// Shape the pages expect from getRequests():
// { requests: [Request], persistence: 'browser' | 'memory' }   newest first
// Request = {
//   id, findingId, requestType, status,      'PENDING' | 'APPROVED' | 'REJECTED'
//   priority,                                'normal' | 'urgent'
//   reason, notes,                           string | null
//   requestedBy, createdAt,                  demo actor label, ISO date string
//   decidedBy, decidedAt, decisionComment,   null until a decision is recorded
//   snapshot: { employeeName, employeeId, system, accountId, classification, severity },
//                                            copy of the finding as it was when the request was made
// }
// createRequest({ findingId, requestType, reason, notes, priority, actorId }) resolves with the new Request.
// decideRequest({ requestId, decision, comment, actorId }) resolves with the updated Request;
//   decision is 'APPROVED' or 'REJECTED'. Both reject with an Error whose message is safe to show.
// Requests are simulated. Nothing here, or anywhere in the app, changes a real account.
//
// These names are the FRONTEND contract. In Milestone 6 the live adapter maps the real
// API fields onto them, so pages never depend on backend field names. Any field the API
// does not supply stays null and the page shows "Not available".
function newestRequestPerFinding(requests) {
  const latest = new Map()
  for (const request of requests) {
    const current = latest.get(request.findingId)
    if (!current || Date.parse(request.createdAt) > Date.parse(current.createdAt)) latest.set(request.findingId, request)
  }
  return latest
}

// Findings carry the status of their newest request, so the table, filters and drawer
// stay in step with the Requests page. Findings without a request keep their original values.
function withRequestStatus(findings, requests) {
  const latest = newestRequestPerFinding(requests)
  return findings.map((item) => {
    const request = latest.get(item.id)
    return request ? { ...item, reviewStatus: request.status, requestId: request.id } : item
  })
}

function newestFirst(requests) {
  return [...requests].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
}

function failIfSaveScenario() {
  if (MOCK_SCENARIO === 'save-error') {
    throw new Error('Simulated error: the demo data source could not save this change. This is a test scenario, not a real failure.')
  }
}

function cleanText(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || null
}

let eventCounter = 0
function makeEvent(type, actor, subject, details) {
  eventCounter += 1
  return { id: `evt-req-${Date.now()}-${eventCounter}`, type, actor, timestamp: new Date().toISOString(), subject, details }
}

export const mockAdapter = {
  async getOverview({ signal } = {}) {
    await delay(LATENCY_MS, signal)
    // Events from requests made in this demo session are mixed in with the starting events.
    const events = [...loadState().events, ...MOCK_AUDIT_EVENTS]
      .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
      .slice(0, 5)
    return {
      scan: MOCK_SCAN,
      counts: MOCK_COUNTS,
      recentEvents: events,
    }
  },

  async getFindings({ signal } = {}) {
    await delay(MOCK_SCENARIO === 'slow' ? SLOW_LATENCY_MS : LATENCY_MS, signal)
    if (MOCK_SCENARIO === 'error') {
      throw new Error('Simulated error: the demo data source did not respond. This is a test scenario, not a real failure.')
    }
    if (MOCK_SCENARIO === 'empty') return { findings: [] }
    return { findings: withRequestStatus(MOCK_FINDINGS, loadState().requests) }
  },

  async getRequests({ signal } = {}) {
    await delay(MOCK_SCENARIO === 'slow' ? SLOW_LATENCY_MS : LATENCY_MS, signal)
    if (MOCK_SCENARIO === 'error') {
      throw new Error('Simulated error: the demo data source did not respond. This is a test scenario, not a real failure.')
    }
    const { requests } = loadState()
    return { requests: MOCK_SCENARIO === 'empty' ? [] : newestFirst(requests), persistence: persistenceMode() }
  },

  async createRequest({ findingId, requestType, reason, notes, priority = 'normal', actorId } = {}) {
    await delay(SAVE_LATENCY_MS)
    failIfSaveScenario()

    const state = loadState()
    const finding = withRequestStatus(MOCK_FINDINGS, state.requests).find((item) => item.id === findingId)
    if (!finding) throw new Error('That finding could not be found, so no request was created.')

    const eligibility = getRequestEligibility(finding)
    if (!eligibility.allowed) throw new Error(eligibility.reason)

    const actor = getRoleById(actorId)
    if (!actor) throw new Error('The request needs a demo role. Choose one in the top bar.')
    if (!REQUEST_TYPES[requestType]) throw new Error('Choose a request type.')
    if (!PRIORITIES[priority]) throw new Error('Choose a priority.')

    const cleanReason = cleanText(reason)
    if (!cleanReason || cleanReason.length < REASON_MIN) throw new Error(`Give a reason of at least ${REASON_MIN} characters.`)
    if (cleanReason.length > TEXT_MAX) throw new Error(`Keep the reason under ${TEXT_MAX} characters.`)
    const cleanNotes = cleanText(notes)
    if (cleanNotes && cleanNotes.length > TEXT_MAX) throw new Error(`Keep the notes under ${TEXT_MAX} characters.`)

    const request = {
      id: nextRequestId(state.requests),
      findingId: finding.id,
      requestType,
      status: 'PENDING',
      priority,
      reason: cleanReason,
      notes: cleanNotes,
      requestedBy: actor.id,
      createdAt: new Date().toISOString(),
      decidedBy: null,
      decidedAt: null,
      decisionComment: null,
      snapshot: {
        employeeName: finding.employeeName,
        employeeId: finding.employeeId,
        system: finding.system,
        accountId: finding.accountId,
        classification: finding.classification,
        severity: finding.severity,
      },
    }
    const event = makeEvent(
      'REQUEST_PREPARED', actor.id, request.id,
      `${getRequestType(requestType).label} request submitted for approval (simulated).`,
    )
    saveState({ requests: [request, ...state.requests], events: [event, ...state.events] })
    return request
  },

  async decideRequest({ requestId, decision, comment, actorId } = {}) {
    await delay(SAVE_LATENCY_MS)
    failIfSaveScenario()

    const state = loadState()
    const index = state.requests.findIndex((item) => item.id === requestId)
    if (index === -1) throw new Error('That request could not be found. It may have been removed by a reset.')
    const current = state.requests[index]
    if (current.status !== 'PENDING') throw new Error(`This request was already ${current.status.toLowerCase()}. A decision cannot be changed.`)

    const actor = getRoleById(actorId)
    if (!actor?.canApprove) throw new Error('Only a demo approver can approve or reject requests. Switch the demo role in the top bar.')
    if (current.requestedBy === actor.id) throw new Error('You raised this request, so a different reviewer must decide it.')
    if (decision !== 'APPROVED' && decision !== 'REJECTED') throw new Error('Choose approve or reject.')

    const cleanComment = cleanText(comment)
    if (decision === 'REJECTED' && !cleanComment) throw new Error('Add a comment explaining why the request is rejected.')
    if (cleanComment && cleanComment.length > TEXT_MAX) throw new Error(`Keep the comment under ${TEXT_MAX} characters.`)

    const updated = {
      ...current,
      status: decision,
      decidedBy: actor.id,
      decidedAt: new Date().toISOString(),
      decisionComment: cleanComment,
    }
    const requests = [...state.requests]
    requests[index] = updated
    const event = makeEvent(
      decision === 'APPROVED' ? 'REQUEST_APPROVED' : 'REQUEST_REJECTED', actor.id, updated.id,
      decision === 'APPROVED'
        ? 'Approval recorded. No account was changed (simulated).'
        : 'Rejection recorded. No account was changed (simulated).',
    )
    saveState({ requests, events: [event, ...state.events] })
    return updated
  },

  // ──────────────────────────────────────────────────────────────────────────
  // Milestone 4: Execution and Verification
  // ──────────────────────────────────────────────────────────────────────────

  // Returns approved requests with their execution status.
  // Shape: { requests: [Request], executions: [Execution], verifications: [Verification], persistence }
  async getExecutionData({ signal } = {}) {
    await delay(MOCK_SCENARIO === 'slow' ? SLOW_LATENCY_MS : LATENCY_MS, signal)
    if (MOCK_SCENARIO === 'error') {
      throw new Error('Simulated error: the demo data source did not respond. This is a test scenario, not a real failure.')
    }
    const { requests } = loadState()
    const { executions, verifications } = loadExecutionState()
    const approved = MOCK_SCENARIO === 'empty' ? [] : requests.filter((r) => r.status === 'APPROVED')
    return {
      requests: newestFirst(approved),
      executions,
      verifications,
      persistence: executionPersistenceMode(),
    }
  },

  // Execute an approved request (simulated).
  // Runs pre-execution checks, records success or failure, and creates an audit event.
  async executeRequest({ requestId, actorId, simulateFailure = false } = {}) {
    await delay(SAVE_LATENCY_MS)
    failIfSaveScenario()

    const reqState = loadState()
    const request = reqState.requests.find((r) => r.id === requestId)
    if (!request) throw new Error('That request could not be found.')

    const actor = getRoleById(actorId)
    if (!actor) throw new Error('Choose a demo role in the top bar before executing.')

    const execState = loadExecutionState()
    const checks = runPreExecutionChecks(request, execState.executions)

    if (!allChecksPassed(checks)) {
      const failedCheck = checks.find((c) => !c.passed)
      throw new Error(`Pre-execution check failed: ${failedCheck.reason}`)
    }

    const now = new Date().toISOString()
    const status = simulateFailure ? 'FAILED' : 'SUCCESS'
    const failureReason = simulateFailure
      ? 'Simulated failure: the execution was intentionally set to fail for demonstration purposes.'
      : null

    const execution = {
      id: nextExecutionId(execState.executions),
      requestId: request.id,
      status,
      executedBy: actor.id,
      executedAt: now,
      failureReason,
      preChecks: checks,
      snapshot: { ...request.snapshot },
      requestType: request.requestType,
      verificationStatus: 'UNVERIFIED',
    }

    saveExecutionState({
      executions: [execution, ...execState.executions],
      verifications: execState.verifications,
    })

    const event = makeEvent(
      status === 'SUCCESS' ? 'EXECUTION_COMPLETED' : 'EXECUTION_FAILED',
      actor.id,
      execution.id,
      status === 'SUCCESS'
        ? `Simulated execution completed for ${request.id}. No account was actually changed.`
        : `Simulated execution failed for ${request.id}. ${failureReason}`,
    )
    addRequestEvent(event)

    return execution
  },

  // Verify an execution result against the original approved request.
  async verifyExecution({ executionId, decision, comment, actorId } = {}) {
    await delay(SAVE_LATENCY_MS)
    failIfSaveScenario()

    const actor = getRoleById(actorId)
    if (!actor) throw new Error('Choose a demo role in the top bar before verifying.')

    const execState = loadExecutionState()
    const execIndex = execState.executions.findIndex((e) => e.id === executionId)
    if (execIndex === -1) throw new Error('That execution record could not be found.')

    const execution = execState.executions[execIndex]
    if (execution.status !== 'SUCCESS') throw new Error('Only successful executions can be verified.')
    if (execution.verificationStatus === 'VERIFIED') throw new Error('This execution has already been verified.')
    if (execution.verificationStatus === 'DISPUTED') throw new Error('This execution has already been disputed.')

    if (execution.executedBy === actor.id) {
      throw new Error('The person who executed a request cannot verify it. Switch the demo role in the top bar.')
    }

    if (decision !== 'VERIFIED' && decision !== 'DISPUTED') throw new Error('Choose verified or disputed.')

    const cleanComment = typeof comment === 'string' ? comment.trim() : ''
    if (decision === 'DISPUTED' && !cleanComment) throw new Error('Add a comment explaining why the execution is disputed.')
    if (cleanComment.length > TEXT_MAX) throw new Error(`Keep the comment under ${TEXT_MAX} characters.`)

    const now = new Date().toISOString()

    const verification = {
      id: nextVerificationId(execState.verifications),
      executionId: execution.id,
      requestId: execution.requestId,
      decision,
      comment: cleanComment || null,
      verifiedBy: actor.id,
      verifiedAt: now,
    }

    // Update the execution's verification status
    const updatedExecutions = [...execState.executions]
    updatedExecutions[execIndex] = { ...execution, verificationStatus: decision }

    saveExecutionState({
      executions: updatedExecutions,
      verifications: [verification, ...execState.verifications],
    })

    const event = makeEvent(
      decision === 'VERIFIED' ? 'EXECUTION_VERIFIED' : 'EXECUTION_DISPUTED',
      actor.id,
      execution.id,
      decision === 'VERIFIED'
        ? `Verification confirmed for ${execution.requestId}. No account was actually changed (simulated).`
        : `Verification disputed for ${execution.requestId}. ${cleanComment}`,
    )
    addRequestEvent(event)

    return { execution: updatedExecutions[execIndex], verification }
  },

  // Returns the combined audit trail across requests, executions and verifications.
  async getAuditTrail({ signal } = {}) {
    await delay(LATENCY_MS, signal)
    const reqEvents = loadState().events
    // Execution and verification events carry the execution id as their subject, so the request id
    // is looked up from the stored execution records. Events are only read here, never created.
    const requestIdByExecution = new Map(loadExecutionState().executions.map((e) => [e.id, e.requestId]))
    const seen = new Set()
    const allEvents = []
    for (const event of [...reqEvents, ...MOCK_AUDIT_EVENTS]) {
      if (seen.has(event.id)) continue
      seen.add(event.id)
      const requestId = /^REQ-/.test(event.subject ?? '') ? event.subject : (requestIdByExecution.get(event.subject) ?? null)
      allEvents.push({ ...event, requestId })
    }
    allEvents.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
    return { events: allEvents, persistence: persistenceMode() }
  },

  // Demo only: puts the starting requests back and clears requests made in this browser.
  async resetDemoRequests() {
    await delay(SAVE_LATENCY_MS)
    resetState()
    resetExecutionState()
    return { ok: true }
  },
}

