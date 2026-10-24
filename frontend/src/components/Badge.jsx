// tone: 'danger' | 'warning' | 'success' | 'neutral' | 'brand'
export default function Badge({ tone = 'neutral', icon: Icon, children }) {
  return (
    <span className={`badge tone-${tone}`}>
      {Icon && <Icon size={13} aria-hidden="true" />}
      {children}
    </span>
  )
}
