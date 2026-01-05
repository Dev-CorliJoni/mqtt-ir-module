import React from 'react'
import { cn } from './cn.js'

export function IconButton({ label, className, ...props }) {
  return (
    <button
      aria-label={label}
      className={cn(
        'inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] text-[rgb(var(--fg))] hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-[rgb(var(--primary))] focus:ring-offset-2 focus:ring-offset-[rgb(var(--bg))]',
        className,
      )}
      {...props}
    />
  )
}