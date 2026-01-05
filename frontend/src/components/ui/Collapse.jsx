import React from 'react'
import { cn } from './cn.js'

export function Collapse({ open, title, children, className, onToggle }) {
  return (
    <div className={cn('rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))]', className)}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold"
      >
        <span>{title}</span>
        <span className="text-[rgb(var(--muted))]">{open ? '–' : '+'}</span>
      </button>
      {open ? <div className="px-3 pb-3">{children}</div> : null}
    </div>
  )
}