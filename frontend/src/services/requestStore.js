import { MOCK_SEED_REQUESTS } from '../data/mockData.js'

// Demo-only storage for requests. It belongs to the mock adapter and nothing else should import it.
// State is { requests: [...], events: [...] } kept in the browser's localStorage so it survives a refresh.
// If localStorage is blocked, the same state is kept in memory and lasts until the page is reloaded.
// The state is re-read on every call, so two open tabs stay in step.
const STORAGE_KEY = 'leaverguard.demo.requests.v1'

let memoryState = null
let storageWorks = true

function seedState() {
  return { requests: MOCK_SEED_REQUESTS.map((request) => ({ ...request, snapshot: { ...request.snapshot } })), events: [] }
}

function isValid(state) {
  return state && Array.isArray(state.requests) && Array.isArray(state.events)
}

export function loadState() {
  let raw = null
  try {
    raw = window.localStorage.getItem(STORAGE_KEY)
    storageWorks = true
  } catch {
    // Blocked storage: keep working from memory, or from the starting data.
    storageWorks = false
    return isValid(memoryState) ? memoryState : seedState()
  }
  if (!raw) return seedState()
  try {
    const parsed = JSON.parse(raw)
    return isValid(parsed) ? parsed : seedState()
  } catch {
    // Saved data that cannot be read is ignored and the starting data is used instead.
    return seedState()
  }
}

export function saveState(state) {
  memoryState = state
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    storageWorks = true
  } catch {
    storageWorks = false
  }
}

export function resetState() {
  memoryState = null
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    storageWorks = false
  }
}

export function persistenceMode() {
  return storageWorks ? 'browser' : 'memory'
}

export function nextRequestId(requests) {
  const highest = requests.reduce((max, request) => {
    const match = /^REQ-DEMO-(\d+)$/.exec(request.id)
    return match ? Math.max(max, Number(match[1])) : max
  }, 0)
  return `REQ-DEMO-${String(highest + 1).padStart(3, '0')}`
}
