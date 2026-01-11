import React, { useRef } from 'react'
import Icon from '@mdi/react'
import { mdiClose } from '@mdi/js'
import { cn } from './cn.js'

export function TextField({ label, hint, className, onClear, clearLabel, ...props }) {
  const inputRef = useRef(null)
  const stringValue =
    typeof props.value === 'string' ? props.value : typeof props.value === 'number' ? String(props.value) : ''
  const hasClearAction = Boolean(onClear) && Boolean(clearLabel)
  // Only show the clear action when the field is editable and has content.
  const canClear = hasClearAction && stringValue.trim().length > 0 && !props.disabled && !props.readOnly
  // Reserve space for the clear button to avoid text jumping when it appears.
  const inputPadding = hasClearAction ? 'pl-3 pr-12' : 'px-3'

  const handleClear = () => {
    onClear?.()
    inputRef.current?.focus()
  }

  return (
    <label className={cn('block', className)}>
      {label ? <div className="mb-1 text-sm font-medium">{label}</div> : null}
      <div className="relative">
        <input
          ref={inputRef}
          className={cn(
            'h-11 w-full rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] text-sm text-[rgb(var(--fg))] outline-none focus:ring-2 focus:ring-[rgb(var(--primary))]',
            inputPadding,
          )}
          {...props}
        />
        {canClear ? (
          <button
            type="button"
            onClick={handleClear}
            aria-label={clearLabel}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-[rgb(var(--muted))] hover:text-[rgb(var(--fg))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--primary))] focus:ring-offset-2 focus:ring-offset-[rgb(var(--bg))]"
          >
            <Icon path={mdiClose} size={0.75} aria-hidden="true" />
          </button>
        ) : null}
      </div>
      {hint ? <div className="mt-1 text-xs text-[rgb(var(--muted))]">{hint}</div> : null}
    </label>
  )
}
