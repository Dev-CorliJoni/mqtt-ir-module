import React, { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import i18n from 'i18next'
import { useTranslation } from 'react-i18next'

import { getAppConfig } from '../utils/appConfig.js'
import { getHealth } from '../api/healthApi.js'
import { getSettings } from '../api/settingsApi.js'
import { BottomNav } from '../components/layout/BottomNav.jsx'
import { SidebarNav } from '../components/layout/SidebarNav.jsx'
import { TopBar } from '../components/layout/TopBar.jsx'
import { Modal } from '../components/ui/Modal.jsx'
import { Button } from '../components/ui/Button.jsx'
import { LearningBar } from '../components/layout/LearningBar.jsx'
import { applyTheme } from '../features/settings/theme.js'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ErrorCallout } from '../components/ui/ErrorCallout.jsx'

export function AppShell() {
  const { t } = useTranslation()
  const toast = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const config = useMemo(() => getAppConfig(), [])

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 5000,
  })

  const settingsQuery = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: 60_000,
  })

  const [offlineOpen, setOfflineOpen] = useState(false)

  useEffect(() => {
    if (healthQuery.isError) setOfflineOpen(true)
  }, [healthQuery.isError])

  useEffect(() => {
    const theme = settingsQuery.data?.theme || 'system'
    applyTheme(theme)
  }, [settingsQuery.data?.theme])

  useEffect(() => {
    const language = settingsQuery.data?.language
    if (!language) return
    i18n.changeLanguage(language).catch(() => {
      toast.show({ title: 'i18n', message: 'Failed to change language.' })
    })
    document.documentElement.lang = language
  }, [settingsQuery.data?.language, toast])

  const learningActive = Boolean(healthQuery.data?.learn_enabled)
  const learningRemoteId = healthQuery.data?.learn_remote_id ?? null
  const learningRemoteName = healthQuery.data?.learn_remote_name ?? null

  return (
    <div className="min-h-dvh">
      <SidebarNav />
      <div className="md:pl-64">
        <TopBar />

        {learningActive ? (
          <div className="px-4 md:px-6 pt-3">
            <LearningBar remoteId={learningRemoteId} remoteName={learningRemoteName} currentPath={location.pathname} onNavigate={navigate} />
          </div>
        ) : null}

        <main className="px-4 md:px-6 pb-24 md:pb-8 pt-4">
          <Outlet />
        </main>

        <BottomNav />
      </div>

      <Modal
        open={offlineOpen}
        title={t('errors.offlineTitle')}
        onClose={() => setOfflineOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setOfflineOpen(false)}>
              {t('common.close')}
            </Button>
            <Button
              onClick={() => {
                healthQuery.refetch()
                settingsQuery.refetch()
              }}
            >
              {t('common.retry')}
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-[rgb(var(--muted))]">{t('errors.offlineBody')}</p>
          {healthQuery.error ? <ErrorCallout error={healthQuery.error} /> : null}
        </div>
      </Modal>
    </div>
  )
}