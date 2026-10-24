import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { DEFAULT_ROLE_KEY, DEMO_ROLES } from '../utils/demoRoles.js'

const STORAGE_KEY = 'leaverguard.demo.role'
const DemoRoleContext = createContext(null)

function readStoredRole() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return DEMO_ROLES[stored] ? stored : DEFAULT_ROLE_KEY
  } catch {
    return DEFAULT_ROLE_KEY
  }
}

// Holds the demo role chosen in the top bar. It decides which buttons the screens show.
// It is not security: anyone can switch it. A real backend must check permissions itself.
export function DemoRoleProvider({ children }) {
  const [roleKey, setRoleKey] = useState(readStoredRole)

  const setRole = useCallback((key) => {
    if (!DEMO_ROLES[key]) return
    setRoleKey(key)
    try {
      window.localStorage.setItem(STORAGE_KEY, key)
    } catch {
      // Storage can be blocked. The choice then lasts until the page is reloaded.
    }
  }, [])

  const value = useMemo(() => ({ role: DEMO_ROLES[roleKey], roleKey, setRole }), [roleKey, setRole])
  return <DemoRoleContext.Provider value={value}>{children}</DemoRoleContext.Provider>
}

export function useDemoRole() {
  const context = useContext(DemoRoleContext)
  if (!context) throw new Error('useDemoRole must be used inside DemoRoleProvider.')
  return context
}
