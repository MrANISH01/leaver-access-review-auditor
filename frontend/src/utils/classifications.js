import { UserX, Eye, Ban, ShieldCheck, Info } from 'lucide-react'

// One place that describes every classification. The wording is a frontend label;
// confirm it against the backend API documentation before the final demo.
export const CLASSIFICATION_ORDER = ['LEAVER_ACTIVE', 'NEEDS_REVIEW', 'EXCLUDED', 'OK']

export const CLASSIFICATIONS = {
  LEAVER_ACTIVE: {
    label: 'Leaver, still active',
    statLabel: 'Requiring action',
    tone: 'danger',
    icon: UserX,
    description: 'The account appears to remain active after the employee left.',
  },
  NEEDS_REVIEW: {
    label: 'Needs review',
    statLabel: 'Needing review',
    tone: 'warning',
    icon: Eye,
    description: 'The match is uncertain. A person must investigate before anything is treated as confirmed.',
  },
  EXCLUDED: {
    label: 'Excluded',
    statLabel: 'Excluded',
    tone: 'neutral',
    icon: Ban,
    description: 'The record is set aside and not queued for remediation.',
  },
  OK: {
    label: 'OK',
    statLabel: 'Classified OK',
    tone: 'success',
    icon: ShieldCheck,
    description: 'No leaver-access issue was detected.',
  },
}

export function getClassification(key) {
  return CLASSIFICATIONS[key] ?? {
    label: key || 'Unknown',
    statLabel: key || 'Unknown',
    tone: 'neutral',
    icon: Info,
    description: 'This classification is not recognised by the frontend yet.',
  }
}
