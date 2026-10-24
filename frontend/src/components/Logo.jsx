export default function Logo() {
  return (
    <div className="logo">
      <svg className="logo__mark" viewBox="0 0 32 32" width="34" height="34" aria-hidden="true">
        <path d="M16 2.5 5 6.6v8.1c0 6.7 4.5 12.2 11 14.8 6.5-2.6 11-8.1 11-14.8V6.6L16 2.5Z" fill="#4f46e5" />
        <path d="M16 2.5 5 6.6v8.1c0 6.7 4.5 12.2 11 14.8Z" fill="#6366f1" />
        <circle cx="16" cy="12.2" r="3.2" fill="#fff" />
        <path d="M9.8 21.2c.9-3 3.4-4.6 6.2-4.6s5.3 1.6 6.2 4.6c-1.7 1.7-3.6 3-6.2 4.1-2.6-1.1-4.5-2.4-6.2-4.1Z" fill="#fff" />
      </svg>
      <div className="logo__text">
        <strong>LeaverGuard</strong>
        <span>Leaver Access Review Auditor</span>
      </div>
    </div>
  )
}
