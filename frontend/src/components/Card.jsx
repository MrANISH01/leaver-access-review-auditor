export default function Card({ title, subtitle, action, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="card__head">
          <div>
            <h2 className="card__title">{title}</h2>
            {subtitle && <p className="card__sub">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="card__body">{children}</div>
    </section>
  )
}
