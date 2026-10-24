import { loadState as loadRequestState, saveState as saveRequestState } from './requestStore.js'

// Demo-only storage for execution and verification records.
// Uses the same localStorage pattern as requestStore.js.
// State shape: { executions: [...], verifications: [...] }
const STORAGE_KEY = 'leaverguard.demo.executions.v1'

let memoryState = null
let storageWorks = true

function seedState() {
  return { executions: [], verifications: [] }
}

function isValid(state) {
  return state && Array.isArray(state.executions) && Array.isArray(state.verifications)
}

export function loadExecutionState() {
  let raw = null
  try {
    raw = window.localStorage.getItem(STORAGE_KEY)
    storageWorks = true
  } catch {
    storageWorks = false
    return isValid(memoryState) ? memoryState : seedState()
  }
  if (!raw) return seedState()
  try {
    const parsed = JSON.parse(raw)
    return isValid(parsed) ? parsed : seedState()
  } catch {
    return seedState()
  }
}

export function saveExecutionState(state) {
  memoryState = state
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    storageWorks = true
  } catch {
    storageWorks = false
  }
}

export function resetExecutionState() {
  memoryState = null
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    storageWorks = false
  }
}

export function executionPersistenceMode() {
  return storageWorks ? 'browser' : 'memory'
}

export function nextExecutionId(executions) {
  const highest = executions.reduce((max, exec) => {
    const match = /^EXEC-DEMO-(\d+)$/.exec(exec.id)
    return match ? Math.max(max, Number(match[1])) : max
  }, 0)
  return `EXEC-DEMO-${String(highest + 1).padStart(3, '0')}`
}

export function nextVerificationId(verifications) {
  const highest = verifications.reduce((max, v) => {
    const match = /^VER-DEMO-(\d+)$/.exec(v.id)
    return match ? Math.max(max, Number(match[1])) : max
  }, 0)
  return `VER-DEMO-${String(highest + 1).padStart(3, '0')}`
}

// Adds execution events to the request store's events array so they appear on the Overview page.
export function addRequestEvent(event) {
  const state = loadRequestState()
  saveRequestState({ ...state, events: [event, ...state.events] })
}
