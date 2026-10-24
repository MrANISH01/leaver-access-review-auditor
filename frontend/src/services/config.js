// Central configuration. Values come from .env.local (see .env.example).
const rawMode = String(import.meta.env.VITE_DATA_MODE || 'demo').toLowerCase()

export const DATA_MODE = rawMode === 'live' ? 'live' : 'demo'
export const IS_DEMO = DATA_MODE === 'demo'

export const API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001/api/v1').replace(/\/+$/, '')

// Demo-only switch for trying out screen states: normal | empty | error | slow | save-error
// empty, error and slow affect the Findings and Requests pages. save-error loads the pages normally
// but makes submitting or deciding a request fail. Ignored in live mode.
const rawScenario = String(import.meta.env.VITE_MOCK_SCENARIO || 'normal').toLowerCase()
export const MOCK_SCENARIO = ['empty', 'error', 'slow', 'save-error'].includes(rawScenario) ? rawScenario : 'normal'
