import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const show = useCallback((toast) => {
    const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
    const item = { id, title: toast.title || '', message: toast.message || '' }
    setToasts((prev) => [...prev, item])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3500)
  }, [])

  const value = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[60] space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="w-[320px] rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] shadow-[var(--shadow)] p-3"
          >
            {t.title ? <div className="font-semibold text-sm">{t.title}</div> : null}
            <div className="text-xs text-[rgb(var(--muted))]">{t.message}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return ctx
}