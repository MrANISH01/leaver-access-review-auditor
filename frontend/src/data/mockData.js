// ALL DATA IN THIS FILE IS SYNTHETIC. It exists only for the demo mode.
// People, accounts and systems are invented. Email-style accounts use the reserved
// "demo.example" domain. The class counts match an earlier local demo scan (16 findings).
// Timestamps are generated relative to "now" so the demo always looks fresh.
const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60_000).toISOString()
const hoursAgo = (hours) => minutesAgo(hours * 60)
const daysAgo = (days) => minutesAgo(days * 1440)

const SCAN_AT = minutesAgo(95)

export const MOCK_SCAN = {
  id: 'demo-scan-001',
  status: 'completed',
  completedAt: SCAN_AT,
}

// Fields a finding may leave empty default to null, which the UI shows as "Not available".
const finding = (data) => ({
  employeeName: null,
  employeeId: null,
  employmentEndDate: null,
  accountStatus: null,
  severity: null,
  matchConfidence: null,
  matchMethod: null,
  reviewStatus: null,
  requestId: null,
  lastSeenAt: null,
  rationale: null,
  exclusionReason: null,
  recommendation: null,
  evidence: [],
  ...data,
})
const ev = (id, label, value, source, observedAt = SCAN_AT) => ({ id, label, value, source, observedAt })

const REC_DISABLE = 'Prepare a request to disable this account and send it for approval.'
const REC_REVIEW = 'A person should confirm whether this account belongs to the departed employee before any request is prepared.'
const REC_NONE = 'No action needed.'
const REC_EXCLUDED = 'No action recommended while this record stays excluded.'
const EXACT_ID = 'Exact employee ID match'
const EMAIL_MATCH = 'Email address match'
const EXCLUDED_RATIONALE = 'This record was excluded from the leaver review.'

export const MOCK_FINDINGS = [
  // ---- Leaver accounts that appear to be still active (7) ----
  finding({
    id: 'F-001', classification: 'LEAVER_ACTIVE', employeeName: 'Maya Fernandez', employeeId: 'EMP-1042',
    employmentEndDate: daysAgo(21), system: 'Cloud Console', accountId: 'mfernandez-admin', accountStatus: 'Enabled',
    severity: 'high', matchConfidence: 0.99, matchMethod: EXACT_ID, reviewStatus: 'NOT_STARTED', lastSeenAt: daysAgo(2),
    rationale: 'Employment has ended, but this administrator account is still enabled and was used after the end date.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Cloud Console'),
      ev('e3', 'Role', 'Administrator', 'Cloud Console'),
      ev('e4', 'Last sign-in', 'Sign-in recorded', 'Cloud Console', daysAgo(2)),
    ],
  }),
  finding({
    id: 'F-002', classification: 'LEAVER_ACTIVE', employeeName: 'Daniel Okafor', employeeId: 'EMP-1107',
    employmentEndDate: daysAgo(34), system: 'Source Code Hosting', accountId: 'dokafor', accountStatus: 'Enabled',
    severity: 'high', matchConfidence: 0.97, matchMethod: EXACT_ID, reviewStatus: 'NOT_STARTED', lastSeenAt: daysAgo(9),
    rationale: 'Employment has ended, but this account still has access to private repositories and was active after the end date.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Source Code Hosting'),
      ev('e3', 'Access', 'Write access to private repositories', 'Source Code Hosting'),
      ev('e4', 'Last activity', 'Code push recorded', 'Source Code Hosting', daysAgo(9)),
    ],
  }),
  finding({
    id: 'F-003', classification: 'LEAVER_ACTIVE', employeeName: 'Lena Fischer', employeeId: 'EMP-1019',
    employmentEndDate: daysAgo(15), system: 'Corporate Email', accountId: 'lena.fischer@demo.example', accountStatus: 'Enabled',
    severity: 'medium', matchConfidence: 0.96, matchMethod: EXACT_ID, reviewStatus: 'APPROVED', requestId: 'REQ-DEMO-003', lastSeenAt: daysAgo(4),
    rationale: 'Employment has ended, but this mailbox account is still enabled.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Corporate Email'),
      ev('e3', 'Last sign-in', 'Sign-in recorded', 'Corporate Email', daysAgo(4)),
    ],
  }),
  finding({
    id: 'F-004', classification: 'LEAVER_ACTIVE', employeeName: 'Omar Haddad', employeeId: 'EMP-1153',
    employmentEndDate: daysAgo(52), system: 'VPN Gateway', accountId: 'ohaddad', accountStatus: 'Enabled',
    severity: 'high', matchConfidence: 0.95, matchMethod: EXACT_ID, reviewStatus: 'NOT_STARTED', lastSeenAt: daysAgo(20),
    rationale: 'Employment ended some time ago and this remote-access account is still enabled.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'VPN Gateway'),
      ev('e3', 'Last connection', 'Connection recorded', 'VPN Gateway', daysAgo(20)),
    ],
  }),
  finding({
    id: 'F-005', classification: 'LEAVER_ACTIVE', employeeName: 'Sofia Rossi', employeeId: 'EMP-1088',
    employmentEndDate: daysAgo(8), system: 'CRM', accountId: 'srossi', accountStatus: 'Enabled',
    severity: 'medium', matchConfidence: 0.93, matchMethod: EMAIL_MATCH, reviewStatus: 'REJECTED', requestId: 'REQ-DEMO-002', lastSeenAt: daysAgo(1),
    rationale: 'Employment has ended, but this CRM account is still enabled and was used recently.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'CRM'),
      ev('e3', 'Last sign-in', 'Sign-in recorded', 'CRM', daysAgo(1)),
    ],
  }),
  finding({
    id: 'F-006', classification: 'LEAVER_ACTIVE', employeeName: 'Anika Rao', employeeId: 'EMP-1121',
    employmentEndDate: daysAgo(27), system: 'Finance System', accountId: 'arao', accountStatus: 'Enabled',
    severity: 'high', matchConfidence: 0.98, matchMethod: EXACT_ID, reviewStatus: 'NOT_STARTED',
    rationale: 'Employment has ended and this finance account is still enabled. The system did not report a last sign-in.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Finance System'),
    ],
  }),
  finding({
    id: 'F-007', classification: 'LEAVER_ACTIVE', employeeName: 'Tomás Silva', employeeId: 'EMP-1064',
    employmentEndDate: daysAgo(11), system: 'Corporate Email', accountId: 'tomas.silva@demo.example', accountStatus: 'Enabled',
    severity: 'low', matchConfidence: 0.91, matchMethod: EMAIL_MATCH, reviewStatus: 'NOT_STARTED', lastSeenAt: daysAgo(6),
    rationale: 'Employment has ended, but this mailbox account is still enabled.',
    recommendation: REC_DISABLE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Corporate Email'),
      ev('e3', 'Last sign-in', 'Sign-in recorded', 'Corporate Email', daysAgo(6)),
    ],
  }),

  // ---- Needs human review (1) ----
  finding({
    id: 'F-008', classification: 'NEEDS_REVIEW', employeeName: 'Sam Rivera',
    system: 'CRM', accountId: 'srivera', accountStatus: 'Enabled',
    severity: 'medium', matchConfidence: 0.62, matchMethod: 'Display name and department match; no shared employee ID',
    reviewStatus: 'NOT_STARTED', lastSeenAt: daysAgo(5),
    rationale: 'Two identity records could belong to this account. The match is not strong enough to treat it as a confirmed leaver account.',
    recommendation: REC_REVIEW,
    evidence: [
      ev('e1', 'Matched on', 'Display name and department', 'Identity matching'),
      ev('e2', 'Employee ID on the account', 'Not present', 'CRM'),
      ev('e3', 'Candidate identities', 'Two records could match', 'Identity matching'),
    ],
  }),

  // ---- Excluded (4) ----
  finding({
    id: 'F-009', classification: 'EXCLUDED', system: 'Cloud Console', accountId: 'svc-backup', accountStatus: 'Enabled',
    lastSeenAt: daysAgo(1), rationale: EXCLUDED_RATIONALE,
    exclusionReason: 'Service account that is not tied to a person.', recommendation: REC_EXCLUDED,
    evidence: [ev('e1', 'Account type', 'Service account', 'Cloud Console')],
  }),
  finding({
    id: 'F-010', classification: 'EXCLUDED', system: 'Cloud Console', accountId: 'breakglass-01', accountStatus: 'Enabled',
    rationale: EXCLUDED_RATIONALE, exclusionReason: 'Emergency (break-glass) account that is kept by design.', recommendation: REC_EXCLUDED,
    evidence: [ev('e1', 'Account type', 'Emergency access account', 'Cloud Console')],
  }),
  finding({
    id: 'F-011', classification: 'EXCLUDED', employeeName: 'Isaac Brandt', employeeId: 'EMP-1130', employmentEndDate: daysAgo(5),
    system: 'VPN Gateway', accountId: 'ibrandt', accountStatus: 'Enabled', matchConfidence: 0.94, matchMethod: EXACT_ID,
    lastSeenAt: daysAgo(2), rationale: EXCLUDED_RATIONALE,
    exclusionReason: 'Contractor with an approved access extension.', recommendation: REC_EXCLUDED,
    evidence: [ev('e1', 'Contract status', 'Access extension on record', 'Identity records')],
  }),
  finding({
    id: 'F-012', classification: 'EXCLUDED', employeeName: 'Noor Ahmed', employeeId: 'EMP-1094', employmentEndDate: daysAgo(40),
    system: 'CRM', accountId: 'nahmed', accountStatus: 'Enabled', matchConfidence: 0.9, matchMethod: EXACT_ID,
    lastSeenAt: hoursAgo(30), rationale: EXCLUDED_RATIONALE, recommendation: REC_EXCLUDED,
    evidence: [ev('e1', 'Account status', 'Enabled', 'CRM')],
  }),

  // ---- OK (4) ----
  finding({
    id: 'F-013', classification: 'OK', employeeName: 'Chloe Dubois', employeeId: 'EMP-1072', employmentEndDate: daysAgo(60),
    system: 'Source Code Hosting', accountId: 'cdubois', accountStatus: 'Disabled', matchConfidence: 0.99, matchMethod: EXACT_ID,
    lastSeenAt: daysAgo(61), rationale: 'The employee has left and the account is already disabled.', recommendation: REC_NONE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Disabled', 'Source Code Hosting'),
    ],
  }),
  finding({
    id: 'F-014', classification: 'OK', employeeName: 'Rahul Verma', employeeId: 'EMP-1035',
    system: 'Corporate Email', accountId: 'rahul.verma@demo.example', accountStatus: 'Enabled', matchConfidence: 0.99, matchMethod: EXACT_ID,
    lastSeenAt: hoursAgo(2), rationale: 'The employee is still employed, so an active account is expected.', recommendation: REC_NONE,
    evidence: [
      ev('e1', 'Employment status', 'Currently employed', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Corporate Email'),
    ],
  }),
  finding({
    id: 'F-015', classification: 'OK', employeeName: 'Elena Petrova', employeeId: 'EMP-1016',
    system: 'Finance System', accountId: 'epetrova', accountStatus: 'Enabled', matchConfidence: 0.98, matchMethod: EXACT_ID,
    lastSeenAt: hoursAgo(5), rationale: 'The employee is still employed, so an active account is expected.', recommendation: REC_NONE,
    evidence: [
      ev('e1', 'Employment status', 'Currently employed', 'Identity records'),
      ev('e2', 'Account status', 'Enabled', 'Finance System'),
    ],
  }),
  finding({
    id: 'F-016', classification: 'OK', employeeName: 'Hana Kim', employeeId: 'EMP-1148', employmentEndDate: daysAgo(90),
    system: 'Cloud Console', accountId: 'hkim', accountStatus: 'Disabled', matchConfidence: 0.97, matchMethod: EXACT_ID,
    lastSeenAt: daysAgo(91), rationale: 'The employee has left and the account is already disabled.', recommendation: REC_NONE,
    evidence: [
      ev('e1', 'Employment status', 'Left the organization', 'Identity records'),
      ev('e2', 'Account status', 'Disabled', 'Cloud Console'),
    ],
  }),
]

// Counted from the findings above so the Overview and the Findings page always agree.
export const MOCK_COUNTS = MOCK_FINDINGS.reduce(
  (counts, item) => {
    counts.total += 1
    counts[item.classification] = (counts[item.classification] ?? 0) + 1
    return counts
  },
  { total: 0, LEAVER_ACTIVE: 0, NEEDS_REVIEW: 0, EXCLUDED: 0, OK: 0 },
)

// Newest first. Event types and actor labels are demo placeholders.
export const MOCK_AUDIT_EVENTS = [
  { id: 'evt-005', type: 'REQUEST_APPROVED', actor: 'demo-approver', timestamp: minutesAgo(25), subject: 'REQ-DEMO-003', details: 'Approval recorded for one account (simulated).' },
  { id: 'evt-004', type: 'REQUEST_REJECTED', actor: 'demo-approver', timestamp: minutesAgo(40), subject: 'REQ-DEMO-002', details: 'Rejected because more evidence was needed (simulated).' },
  { id: 'evt-003', type: 'REQUEST_PREPARED', actor: 'demo-analyst', timestamp: minutesAgo(70), subject: 'REQ-DEMO-003', details: 'Remediation request prepared (simulated).' },
  { id: 'evt-002', type: 'REQUEST_PREPARED', actor: 'demo-analyst', timestamp: minutesAgo(80), subject: 'REQ-DEMO-002', details: 'Remediation request prepared (simulated).' },
  { id: 'evt-001', type: 'SCAN_COMPLETED', actor: 'demo-analyst', timestamp: SCAN_AT, subject: 'demo-scan-001', details: `${MOCK_COUNTS.total} findings recorded by a read-only scan.` },
]

// ---- Demo requests (Milestone 3) ---------------------------------------------------------
// These two match the review statuses already shown on findings F-005 and F-003, and the
// REQUEST_REJECTED / REQUEST_APPROVED events above. New requests created in the demo are stored
// by services/requestStore.js, not here. Nothing in this workflow changes a real account.
const snapshotOf = (findingId) => {
  const item = MOCK_FINDINGS.find((entry) => entry.id === findingId)
  return {
    employeeName: item.employeeName,
    employeeId: item.employeeId,
    system: item.system,
    accountId: item.accountId,
    classification: item.classification,
    severity: item.severity,
  }
}

export const MOCK_SEED_REQUESTS = [
  {
    id: 'REQ-DEMO-003', findingId: 'F-003', requestType: 'DISABLE_ACCOUNT', status: 'APPROVED', priority: 'normal',
    reason: 'Employment ended two weeks ago and the mailbox account is still enabled.', notes: null,
    requestedBy: 'demo-analyst', createdAt: minutesAgo(70),
    decidedBy: 'demo-approver', decidedAt: minutesAgo(25), decisionComment: 'Approved. The end date matches the identity records (simulated).',
    snapshot: snapshotOf('F-003'),
  },
  {
    id: 'REQ-DEMO-002', findingId: 'F-005', requestType: 'DISABLE_ACCOUNT', status: 'REJECTED', priority: 'normal',
    reason: 'Employment has ended but the CRM account is still enabled and was used recently.', notes: null,
    requestedBy: 'demo-analyst', createdAt: minutesAgo(80),
    decidedBy: 'demo-approver', decidedAt: minutesAgo(40), decisionComment: 'More evidence is needed before disabling a recently used account (simulated).',
    snapshot: snapshotOf('F-005'),
  },
]
