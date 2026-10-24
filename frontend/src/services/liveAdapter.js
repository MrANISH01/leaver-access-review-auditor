// Placeholder for the real Flask API. No endpoints are invented here.
// Milestone 6: build this from the backend's docs/api.md, normalise the responses
// into the same shapes the mock adapter returns, and add timeouts and error mapping.
function notConnected() {
  return Promise.reject(
    new Error('Live mode is not connected yet. Set VITE_DATA_MODE=demo to use the demo data, or wait for the API integration step.'),
  )
}

export const liveAdapter = {
  getOverview: notConnected,
  getFindings: notConnected,
  getRequests: notConnected,
  createRequest: notConnected,
  decideRequest: notConnected,
  getExecutionData: notConnected,
  executeRequest: notConnected,
  verifyExecution: notConnected,
  getAuditTrail: notConnected,
  resetDemoRequests: notConnected,
}
