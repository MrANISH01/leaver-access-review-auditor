import { NavLink } from 'react-router-dom'
import { Lock, X } from 'lucide-react'
import Logo from './Logo.jsx'
import { NAV_GROUPS, NAV_ITEMS } from '../layouts/navItems.js'

export default function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Primary">
      <div className="sidebar__head">
        <Logo />
        <button type="button" className="icon-btn icon-btn--dark sidebar__close" onClick={onClose} aria-label="Close navigation menu">
          <X size={18} />
        </button>
      </div>

      <nav className="nav" aria-label="Main navigation">
        {NAV_GROUPS.map((group) => (
          <div key={group}>
            <p className="nav__label">{group}</p>
            {NAV_ITEMS.filter((item) => item.group === group).map((item) => {
              const Icon = item.icon
              return (
                <NavLink key={item.to} to={item.to} end={item.to === '/'} className="nav__link" onClick={onClose}>
                  <Icon size={18} aria-hidden="true" />
                  {item.label}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar__note">
        <Lock size={16} aria-hidden="true" />
        <p>
          <strong>Disable-only design</strong>
          LeaverGuard has no account-deletion capability.
        </p>
      </div>
    </aside>
  )
}
