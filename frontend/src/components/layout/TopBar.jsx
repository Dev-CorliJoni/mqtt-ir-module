import React, { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ThemeToggle } from '../pickers/ThemeToggle.jsx'
import { LanguagePicker } from '../pickers/LanguagePicker.jsx'

function getTitle(pathname, t) {
  if (pathname === '/' || pathname === '') return t('nav.home')
  if (pathname.startsWith('/remotes')) return t('nav.remotes')
  if (pathname.startsWith('/settings')) return t('nav.settings')
  return 'mqtt-ir-module'
}

export function TopBar() {
  const { t } = useTranslation()
  const location = useLocation()

  return (
    <div className="sticky top-0 z-30 border-b border-[rgb(var(--border))] bg-[rgb(var(--card))]">
      <div className="h-14 px-4 md:px-6 flex items-center justify-between gap-3">
        <div className="font-semibold">{getTitle(location.pathname, t)}</div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <LanguagePicker />
        </div>
      </div>
    </div>
  )
}