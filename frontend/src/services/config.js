// Central configuration. Values come from .env.local (see .env.example) or environment variables.
const defaultMode = import.meta.env.PROD ? 'live' : 'demo'
const rawMode = String(import.meta.env.VITE_DATA_MODE || defaultMode).toLowerCase()

export const DATA_MODE = rawMode === 'demo' ? 'demo' : 'live'
export const IS_DEMO = DATA_MODE === 'demo'

const defaultApiBaseUrl = import.meta.env.PROD ? '/api/v1' : 'http://127.0.0.1:5001/api/v1'
export const API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl).replace(/\/+$/, '')

// Demo-only switch for trying out screen states: normal | empty | error | slow | save-error
// empty, error and slow affect the Findings and Requests pages. save-error loads the pages normally
// but makes submitting or deciding a request fail. Ignored in live mode.
const rawScenario = String(import.meta.env.VITE_MOCK_SCENARIO || 'normal').toLowerCase()
export const MOCK_SCENARIO = ['empty', 'error', 'slow', 'save-error'].includes(rawScenario) ? rawScenario : 'normal'
