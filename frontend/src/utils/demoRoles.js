// Demo roles. These are labels, NOT real authentication or authorization.
// The ids match the actor labels already used in the demo audit events.
export const DEMO_ROLES = {
  analyst: {
    key: 'analyst',
    id: 'demo-analyst',
    label: 'Demo analyst',
    canApprove: false,
    summary: 'Can start requests. Cannot approve or reject them.',
  },
  approver: {
    key: 'approver',
    id: 'demo-approver',
    label: 'Demo approver',
    canApprove: true,
    summary: 'Can approve or reject requests raised by someone else.',
  },
}

export const DEFAULT_ROLE_KEY = 'analyst'

export function getRoleById(id) {
  return Object.values(DEMO_ROLES).find((role) => role.id === id) ?? null
}
