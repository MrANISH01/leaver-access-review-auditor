import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar.jsx'
import TopBar from '../components/TopBar.jsx'
import DemoBanner from '../components/DemoBanner.jsx'

export default function AppShell() {
  const [navOpen, setNavOpen] = useState(false)

  // Close the mobile menu with the Escape key.
  useEffect(() => {
    if (!navOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setNavOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navOpen])

  return (
    <div className="shell">
      <a className="skip-link" href="#main">Skip to main content</a>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      {navOpen && <div className="scrim" onClick={() => setNavOpen(false)} aria-hidden="true" />}
      <div className="shell__main">
        <TopBar onMenu={() => setNavOpen(true)} />
        <DemoBanner />
        <main id="main" className="content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
