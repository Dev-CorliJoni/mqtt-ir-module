import React from 'react'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiAlertCircleOutline, mdiShieldKeyOutline, mdiTimerOutline, mdiHelpCircleOutline } from '@mdi/js'
import { ApiErrorMapper } from '../../utils/apiErrorMapper.js'

export function ErrorCallout({ error }) {
  const { t } = useTranslation()
  const errorMapper = new ApiErrorMapper(t)
  const { title, body, kind } = errorMapper.getCallout(error)

  // Map error categories to icons so callouts stay consistent across the UI.
  let iconPath = mdiHelpCircleOutline
  if (kind === 'offline') {
    iconPath = mdiAlertCircleOutline
  } else if (kind === 'unauthorized') {
    iconPath = mdiShieldKeyOutline
  } else if (kind === 'timeout') {
    iconPath = mdiTimerOutline
  } else if (kind === 'conflict' || kind === 'notFound') {
    iconPath = mdiAlertCircleOutline
  }

  return (
    <div className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3">
      <div className="flex gap-3 items-start">
        <Icon path={iconPath} size={1} />
        <div className="min-w-0">
          <div className="font-semibold text-sm">{title}</div>
          <div className="text-xs text-[rgb(var(--muted))] break-words">{body}</div>
        </div>
      </div>
    </div>
  )
}
