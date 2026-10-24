import { LayoutDashboard, ListChecks, ClipboardCheck, Play, ScrollText, Settings } from 'lucide-react'

export const NAV_GROUPS = ['Audit', 'Workflow', 'Governance']

export const NAV_ITEMS = [
  {
    to: '/', label: 'Overview', group: 'Audit', icon: LayoutDashboard, milestone: 1,
    title: 'Audit overview',
    blurb: 'Where the leaver-access audit stands right now.',
  },
  {
    to: '/findings', label: 'Findings', group: 'Audit', icon: ListChecks, milestone: 2,
    title: 'Findings and access review',
    blurb: 'Search, filter and inspect every account the audit looked at, with the evidence behind each classification.',
  },
  {
    to: '/requests', label: 'Requests', group: 'Workflow', icon: ClipboardCheck, milestone: 3,
    title: 'Requests and approvals',
    blurb: 'Requests raised from findings, and the approve or reject decisions made on them.',
  },
  {
    to: '/execution', label: 'Execution and verification', group: 'Workflow', icon: Play, milestone: 4,
    title: 'Execution and verification',
    blurb: 'Pre-execution rechecks, execution results and independent verification.',
  },
  {
    to: '/audit-trail', label: 'Audit trail', group: 'Governance', icon: ScrollText, milestone: 5,
    title: 'Audit trail',
    blurb: 'A chronological record of what happened and who performed each recorded action.',
  },
  {
    to: '/settings', label: 'System status', group: 'Governance', icon: Settings, milestone: 5,
    title: 'System status',
    blurb: 'Data mode, API connection and backend health.',
  },
]
