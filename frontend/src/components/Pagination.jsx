import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page, pageCount, start, end, total, allTotal, onChange }) {
  return (
    <nav className="pagination" aria-label="Findings pages">
      <p aria-live="polite">
        Showing <strong>{total ? start + 1 : 0}</strong> to <strong>{end}</strong> of <strong>{total}</strong> findings
        {allTotal !== total && ` (filtered from ${allTotal})`}
      </p>
      <div className="pagination__controls">
        <button type="button" className="btn btn--secondary btn--small" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          <ChevronLeft size={16} aria-hidden="true" /> Previous
        </button>
        <span>Page {page} of {pageCount}</span>
        <button type="button" className="btn btn--secondary btn--small" disabled={page >= pageCount} onClick={() => onChange(page + 1)}>
          Next <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}
