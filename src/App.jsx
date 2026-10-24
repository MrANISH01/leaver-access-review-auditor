import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './layouts/AppShell.jsx'
import { NAV_ITEMS } from './layouts/navItems.js'
import Overview from './pages/Overview.jsx'
import Findings from './pages/Findings.jsx'
import Requests from './pages/Requests.jsx'
import Execution from './pages/Execution.jsx'
import { DemoRoleProvider } from './context/DemoRole.jsx'
import AuditTrail from './pages/AuditTrail.jsx'
import SystemStatus from './pages/SystemStatus.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'

// Screens that are fully built. Every other menu item still shows a PlaceholderPage.
const BUILT = ['/', '/findings', '/requests', '/execution', '/audit-trail', '/settings']

export default function App() {
  return (
    <DemoRoleProvider>
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="/findings" element={<Findings />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/execution" element={<Execution />} />
        <Route path="/audit-trail" element={<AuditTrail />} />
        <Route path="/settings" element={<SystemStatus />} />
        <Route path="/reviews" element={<Navigate to="/requests" replace />} />
        {NAV_ITEMS.filter((item) => !BUILT.includes(item.to)).map((item) => (
          <Route key={item.to} path={item.to} element={<PlaceholderPage item={item} />} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </DemoRoleProvider>
  )
}
