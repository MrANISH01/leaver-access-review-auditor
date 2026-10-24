import { useLocation } from 'react-router-dom'
import { Menu, User } from 'lucide-react'
import ModeBadge from './ModeBadge.jsx'
import { useDemoRole } from '../context/DemoRole.jsx'
import { DEMO_ROLES } from '../utils/demoRoles.js'
import { NAV_ITEMS } from '../layouts/navItems.js'

export default function TopBar({ onMenu }) {
  const { pathname } = useLocation()
  const current = NAV_ITEMS.find((item) => item.to === pathname)
  const { roleKey, setRole } = useDemoRole()

  return (
    <header className="topbar">
      <button type="button" className="icon-btn topbar__menu" onClick={onMenu} aria-label="Open navigation menu">
        <Menu size={18} />
      </button>
      <p className="crumbs">
        LeaverGuard <span aria-hidden="true">/</span> <strong>{current ? current.label : 'Not found'}</strong>
      </p>
      <div className="topbar__spacer" />
      <ModeBadge />
      <label className="actor-chip actor-chip--select" title="A demo role label. It decides which buttons you see and is not real authentication.">
        <User size={14} aria-hidden="true" />
        <span className="sr-only">Demo role</span>
        <select value={roleKey} onChange={(event) => setRole(event.target.value)} aria-label="Demo role">
          {Object.values(DEMO_ROLES).map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
        <span className="actor-chip__extra">(not authenticated)</span>
      </label>
    </header>
  )
}
