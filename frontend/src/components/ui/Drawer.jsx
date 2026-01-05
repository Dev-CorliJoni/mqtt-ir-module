import React, { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { cn } from './cn.js'

export function Drawer({ open, title, children, footer, onClose }) {
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
      <div className="absolute inset-x-0 bottom-0 md:inset-y-0 md:right-0 md:left-auto flex md:items-stretch items-end">
        <div className={cn('w-full md:w-[420px] max-h-[90dvh] md:max-h-none rounded-t-2xl md:rounded-none md:rounded-l-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] shadow-[var(--shadow)] flex flex-col')}>
          {title ? <div className="px-4 py-3 border-b border-[rgb(var(--border))] font-semibold">{title}</div> : null}
          <div className="p-4 overflow-auto">{children}</div>
          {footer ? <div className="px-4 py-3 border-t border-[rgb(var(--border))]">{footer}</div> : null}
        </div>
      </div>
    </div>,
    document.body,
  )
}