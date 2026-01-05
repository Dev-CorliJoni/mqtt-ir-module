import React from 'react'
import { cn } from './cn.js'

export function TextField({ label, hint, className, ...props }) {
  return (
    <label className={cn('block', className)}>
      {label ? <div className="mb-1 text-sm font-medium">{label}</div> : null}
      <input
        className="h-11 w-full rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] px-3 text-sm text-[rgb(var(--fg))] outline-none focus:ring-2 focus:ring-[rgb(var(--primary))]"
        {...props}
      />
      {hint ? <div className="mt-1 text-xs text-[rgb(var(--muted))]">{hint}</div> : null}
    </label>
  )
}