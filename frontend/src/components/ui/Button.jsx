import React from 'react'
import { cn } from './cn.js'

export function Button({ variant = 'primary', size = 'md', disabled, className, ...props }) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition focus:outline-none focus:ring-2 focus:ring-[rgb(var(--primary))] focus:ring-offset-2 focus:ring-offset-[rgb(var(--bg))] disabled:opacity-50 disabled:pointer-events-none'

  const variants = {
    primary: 'bg-[rgb(var(--primary))] text-[rgb(var(--primary-contrast))] hover:opacity-95',
    secondary: 'bg-[rgb(var(--card))] text-[rgb(var(--fg))] border border-[rgb(var(--border))] hover:opacity-95',
    danger: 'bg-[rgb(var(--danger))] text-white hover:opacity-95',
    ghost: 'bg-transparent text-[rgb(var(--fg))] hover:bg-[rgb(var(--card))]',
  }

  const sizes = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-11 px-4 text-sm',
    lg: 'h-12 px-5 text-base',
  }

  return <button disabled={disabled} className={cn(base, variants[variant], sizes[size], className)} {...props} />
}