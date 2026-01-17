import React from 'react'
import { cn } from './cn.js'

export function SelectField({ label, hint, className, children, ...props }) {
  return (
    <label className={cn('block', className)}>
      {label ? <div className="mb-1 text-sm font-medium">{label}</div> : null}
      <select
        className="h-11 w-full rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] px-3 text-sm text-[rgb(var(--fg))] outline-none focus:ring-2 focus:ring-[rgb(var(--primary))]"
        {...props}
      >
        {children}
      </select>
      {hint ? <div className="mt-1 text-xs text-[rgb(var(--muted))]">{hint}</div> : null}
    </label>
  )
}
