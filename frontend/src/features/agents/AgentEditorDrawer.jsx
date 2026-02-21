import React, { useState } from 'react'
import Icon from '@mdi/react'
import { mdiImageEditOutline } from '@mdi/js'
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

export function AgentEditorDrawer({ agent, onClose }) {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const errorMapper = new ApiErrorMapper(t)

  const [name, setName] = useState(typeof agent.name === 'string' ? agent.name : '')
  const [icon, setIcon] = useState(agent.icon ?? null)
  const [configurationUrl, setConfigurationUrl] = useState(typeof agent.configuration_url === 'string' ? agent.configuration_url : '')
  const [iconPickerOpen, setIconPickerOpen] = useState(false)

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

          <TextField
            label={t('agents.configurationUrlLabel')}
            hint={t('agents.configurationUrlHint')}
            value={configurationUrl}
            onChange={(event) => setConfigurationUrl(event.target.value)}
          />
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
