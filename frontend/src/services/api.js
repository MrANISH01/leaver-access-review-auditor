import { IS_DEMO } from './config.js'
import { mockAdapter } from './mockAdapter.js'
import { liveAdapter } from './liveAdapter.js'

// Pages import `api` and never know whether data is synthetic or live.
// Both adapters must offer the same methods and return the same shapes.
export const api = IS_DEMO ? mockAdapter : liveAdapter
