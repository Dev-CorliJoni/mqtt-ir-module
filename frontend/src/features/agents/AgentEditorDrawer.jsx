import React, { useState } from 'react'
import Icon from '@mdi/react'
import { mdiAutorenew, mdiImageEditOutline } from '@mdi/js'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Drawer } from '../../components/ui/Drawer.jsx'
import { TextField } from '../../components/ui/TextField.jsx'
import { Button } from '../../components/ui/Button.jsx'
import { IconButton } from '../../components/ui/IconButton.jsx'
import { IconPicker } from '../../components/pickers/IconPicker.jsx'
import { updateAgent } from '../../api/agentsApi.js'
import { useToast } from '../../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../../utils/apiErrorMapper.js'
import { DEFAULT_AGENT_ICON } from '../../icons/iconRegistry.js'
import { getAppConfig } from '../../utils/appConfig.js'

export function AgentEditorDrawer({ agent, onClose }) {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const errorMapper = new ApiErrorMapper(t)

  const [name, setName] = useState(typeof agent.name === 'string' ? agent.name : '')
  const [icon, setIcon] = useState(agent.icon ?? null)
  const [configurationUrl, setConfigurationUrl] = useState(typeof agent.configuration_url === 'string' ? agent.configuration_url : '')
  const [iconPickerOpen, setIconPickerOpen] = useState(false)
  const appConfig = getAppConfig()

  const fillCurrentUrl = () => {
    if (typeof window === 'undefined') return
    const baseUrl = appConfig.publicBaseUrl.endsWith('/') ? appConfig.publicBaseUrl : `${appConfig.publicBaseUrl}/`
    const path = `${baseUrl}agent/${encodeURIComponent(agent.agent_id)}`
    const absoluteUrl = `${window.location.origin}${path}`
    setConfigurationUrl(absoluteUrl)
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAgent(agent.agent_id, {
        name: name.trim() || null,
        icon: icon ?? null,
        configuration_url: configurationUrl.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['agent', agent.agent_id] })
      toast.show({ title: t('agents.pageTitle'), message: t('common.saved') })
      onClose()
    },
    onError: (error) => {
      toast.show({ title: t('agents.pageTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  if (!agent) return null

  return (
    <>
      <Drawer
        open
        title={`${t('common.edit')}: ${agent.name || agent.agent_id}`}
        onClose={onClose}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold">{t('common.icon')}</div>
            <IconButton label={t('common.icon')} onClick={() => setIconPickerOpen(true)}>
              <Icon path={mdiImageEditOutline} size={1} />
            </IconButton>
          </div>

          <TextField
            label={t('remotes.name')}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />

          <label className="block">
            <div className="mb-1 text-sm font-medium">{t('agents.configurationUrlLabel')}</div>
            <div className="relative">
              <input
                className="h-11 w-full rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] px-3 pr-12 text-sm text-[rgb(var(--fg))] outline-none focus:ring-2 focus:ring-[rgb(var(--primary))]"
                value={configurationUrl}
                onChange={(event) => setConfigurationUrl(event.target.value)}
              />
              <button
                type="button"
                aria-label={t('agents.configurationUrlAuto')}
                title={t('agents.configurationUrlAuto')}
                onClick={fillCurrentUrl}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-[rgb(var(--muted))] hover:text-[rgb(var(--fg))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--primary))] focus:ring-offset-2 focus:ring-offset-[rgb(var(--bg))]"
              >
                <Icon path={mdiAutorenew} size={0.8} />
              </button>
            </div>
            <div className="mt-1 text-xs text-[rgb(var(--muted))]">{t('agents.configurationUrlHint')}</div>
          </label>
        </div>
      </Drawer>

      <IconPicker
        open={iconPickerOpen}
        title={t('common.icon')}
        initialIconKey={icon || DEFAULT_AGENT_ICON}
        onClose={() => setIconPickerOpen(false)}
        onSelect={(key) => {
          setIcon(key)
          setIconPickerOpen(false)
        }}
      />
    </>
  )
}
