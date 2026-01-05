import React, { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { cn } from './cn.js'

export function Modal({ open, title, children, footer, onClose }) {
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={() => onClose?.()} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className={cn('w-full max-w-lg rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] shadow-[var(--shadow)]')}>
          {title ? <div className="px-4 py-3 border-b border-[rgb(var(--border))] font-semibold">{title}</div> : null}
          <div className="p-4">{children}</div>
          {footer ? <div className="px-4 py-3 border-t border-[rgb(var(--border))]">{footer}</div> : null}
        </div>
      </div>
    </div>,
    document.body,
  )
}