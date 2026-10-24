import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, ListChecks, RefreshCw } from 'lucide-react'
import { api } from '../services/api.js'
import useAsync from '../hooks/useAsync.js'
import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import StatCard from '../components/StatCard.jsx'
import ClassificationBreakdown from '../components/ClassificationBreakdown.jsx'
import ScanStatusCard from '../components/ScanStatusCard.jsx'
import RecentActivity from '../components/RecentActivity.jsx'
import { EmptyState, ErrorState, Skeleton } from '../components/States.jsx'
import { CLASSIFICATION_ORDER, CLASSIFICATIONS } from '../utils/classifications.js'

function LoadingRows({ rows = 4 }) {
  return (
    <div className="skeleton-stack" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => <Skeleton key={index} height={18} />)}
    </div>
  )
}

export default function Overview() {
  const { data, loading, error, reload } = useAsync(api.getOverview)
  const [scanning, setScanning] = useState(false)
  const [scanNotice, setScanNotice] = useState(null)
  const counts = data?.counts

  async function handleRunScan() {
    if (scanning) return
    setScanning(true)
    setScanNotice(null)
    try {
      if (typeof api.triggerScan === 'function') {
        await api.triggerScan()
        setScanNotice('Scan completed. Findings and summary updated.')
        reload()
      }
    } catch (err) {
      setScanNotice(`Scan failed: ${err.message}`)
    } finally {
      setScanning(false)
    }
  }

  const header = (
    <PageHeader
      title="Audit overview"
      description="Accounts that belong to people who have left the organization, and what still needs a decision."
      actions={
        <>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={handleRunScan}
            disabled={loading || scanning}
            title="Run a read-only audit scan now"
          >
            <RefreshCw size={16} aria-hidden="true" /> {scanning ? 'Scanning…' : 'Run scan'}
          </button>
          <Link to="/findings" className="btn btn--primary">View findings</Link>
        </>
      }
    />
  )

  if (error) {
    return (
      <>
        {header}
        <Card><ErrorState error={error} onRetry={reload} /></Card>
      </>
    )
  }

  return (
    <>
      {header}

      {scanNotice && (
        <div className="callout tone-brand" role="status" style={{ marginBottom: 16 }}>
          <CheckCircle2 size={18} aria-hidden="true" />
          <p>{scanNotice}</p>
        </div>
      )}

      <section className="stat-grid" aria-label="Audit summary">
        <StatCard label="Total findings" value={counts?.total} icon={ListChecks} tone="brand" to="/findings" loading={loading} />
        {CLASSIFICATION_ORDER.map((key) => {
          const info = CLASSIFICATIONS[key]
          return (
            <StatCard
              key={key}
              label={info.statLabel}
              value={counts?.[key]}
              icon={info.icon}
              tone={info.tone}
              to={`/findings?classification=${key}`}
              loading={loading}
              emphasis={key === 'LEAVER_ACTIVE'}
            />
          )
        })}
      </section>

      <div className="grid-2">
        <Card title="Findings by classification" subtitle="How the audit classified every account it looked at.">
          {loading && <LoadingRows rows={5} />}
          {!loading && counts && counts.total === 0 && (
            <EmptyState title="No findings yet" text="Run a scan to see how accounts are classified." />
          )}
          {!loading && counts && counts.total > 0 && <ClassificationBreakdown counts={counts} />}
        </Card>

        <Card title="Latest scan" subtitle="Status of the most recent audit scan.">
          {loading ? <LoadingRows rows={3} /> : <ScanStatusCard scan={data?.scan} />}
        </Card>
      </div>

      <Card
        title="Recent audit activity"
        subtitle="Actor names are demo labels, not verified identities."
        action={<Link to="/audit-trail" className="btn btn--secondary">Open audit trail</Link>}
      >
        {loading ? <LoadingRows rows={4} /> : <RecentActivity events={data?.recentEvents ?? []} />}
      </Card>
    </>
  )
}
