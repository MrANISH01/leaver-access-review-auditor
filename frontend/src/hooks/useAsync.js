import { useCallback, useEffect, useState } from 'react'

// Runs an async loader and reports { data, loading, error, reload }.
// The loader receives { signal } so an unmounted page can cancel its request.
export default function useAsync(loader) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    loader({ signal: controller.signal })
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error?.name === 'AbortError') return
        setState({ data: null, error, loading: false })
      })
    return () => controller.abort()
  }, [loader, attempt])

  const reload = useCallback(() => {
    setState((previous) => ({ ...previous, error: null, loading: true }))
    setAttempt((value) => value + 1)
  }, [])

  return { ...state, reload }
}
