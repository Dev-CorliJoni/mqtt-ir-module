import React from 'react'
import { cn } from './cn.js'

export function Card({ className, ...props }) {
  return <div className={cn('rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] shadow-[var(--shadow)]', className)} {...props} />
}

export function CardHeader({ className, ...props }) {
  return <div className={cn('px-4 py-3 border-b border-[rgb(var(--border))] flex items-center justify-between gap-3', className)} {...props} />
}

export function CardTitle({ className, ...props }) {
  return <div className={cn('font-semibold', className)} {...props} />
}

export function CardBody({ className, ...props }) {
  return <div className={cn('p-4', className)} {...props} />
}