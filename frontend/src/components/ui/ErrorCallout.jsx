import React from 'react'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiAlertCircleOutline, mdiShieldKeyOutline, mdiTimerOutline, mdiHelpCircleOutline } from '@mdi/js'

export function ErrorCallout({ error }) {
  const { t } = useTranslation()

  const status = error?.status ?? 0
  const detail = error?.message || String(error)

  let title = t('errors.badRequestTitle')
  let body = detail
  let iconPath = mdiHelpCircleOutline

  if (status === 0) {
    title = t('errors.offlineTitle')
    body = t('errors.offlineBody')
    iconPath = mdiAlertCircleOutline
  } else if (status === 401) {
    title = t('errors.unauthorizedTitle')
    body = t('errors.unauthorizedBody')
    iconPath = mdiShieldKeyOutline
  } else if (status === 408) {
    title = t('errors.timeoutTitle')
    body = t('errors.timeoutBody')
    iconPath = mdiTimerOutline
  } else if (status === 409) {
    title = t('errors.conflictTitle')
    body = detail || t('errors.conflictBody')
    iconPath = mdiAlertCircleOutline
  } else if (status === 404) {
    title = t('errors.notFoundTitle')
    body = detail
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