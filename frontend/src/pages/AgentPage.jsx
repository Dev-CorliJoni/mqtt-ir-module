import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { getAgent, updateAgent } from '../api/agentsApi.js'
import { listRemotes } from '../api/remotesApi.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { TextField } from '../components/ui/TextField.jsx'
import { Button } from '../components/ui/Button.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'
import { getAppConfig } from '../utils/appConfig.js'

export function AgentPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const errorMapper = new ApiErrorMapper(t)
  const { agentId = '' } = useParams()

  const appConfig = useMemo(() => getAppConfig(), [])

  const agentQuery = useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => getAgent(agentId),
    enabled: Boolean(agentId),
  })
  const remotesQuery = useQuery({ queryKey: ['remotes'], queryFn: listRemotes })

  const [agentName, setAgentName] = useState('')
  const [configurationUrl, setConfigurationUrl] = useState('')

  useEffect(() => {
    if (!agentQuery.data) return
    setAgentName(typeof agentQuery.data.name === 'string' ? agentQuery.data.name : '')
    setConfigurationUrl(typeof agentQuery.data.configuration_url === 'string' ? agentQuery.data.configuration_url : '')
  }, [agentQuery.data])

  const saveMutation = useMutation({
    mutationFn: () => updateAgent(agentId, { name: agentName.trim() || null, configuration_url: configurationUrl.trim() || null }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['agent', agentId], updated)
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.show({ title: t('agents.pageTitle'), message: t('common.saved') })
    },
    onError: (error) => {
      toast.show({ title: t('agents.pageTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const assignedRemotes = useMemo(() => {
    const remotes = remotesQuery.data || []
    return remotes.filter((remote) => String(remote.assigned_agent_id || '') === agentId)
  }, [remotesQuery.data, agentId])

  const isLoading = agentQuery.isLoading
  const hasAgent = Boolean(agentQuery.data)
  const initialName = typeof agentQuery.data?.name === 'string' ? agentQuery.data.name : ''
  const initialValue = typeof agentQuery.data?.configuration_url === 'string' ? agentQuery.data.configuration_url : ''
  const hasChanges = configurationUrl.trim() !== initialValue || agentName.trim() !== initialName

  const fillCurrentUrl = () => {
    if (typeof window === 'undefined') return
    const baseUrl = appConfig.publicBaseUrl.endsWith('/') ? appConfig.publicBaseUrl : `${appConfig.publicBaseUrl}/`
    const path = `${baseUrl}agent/${encodeURIComponent(agentId)}`
    const absoluteUrl = `${window.location.origin}${path}`
    setConfigurationUrl(absoluteUrl)
  }

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <div className="text-sm text-[rgb(var(--muted))]">{t('common.loading')}</div>
        </CardBody>
      </Card>
    )
  }

  if (agentQuery.isError || !hasAgent) {
    return (
      <Card>
        <CardBody className="space-y-3">
          <div className="text-sm text-[rgb(var(--muted))]">{t('errors.notFoundTitle')}</div>
          <div>
            <Button variant="secondary" onClick={() => navigate('/settings')}>
              {t('settings.agentTitle')}
            </Button>
          </div>
        </CardBody>
      </Card>
    )
  }

  const agent = agentQuery.data
  const agentLabel = agent.name || agent.agent_id

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t('agents.pageTitle')}</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="text-sm font-semibold">{agentLabel}</div>
          <div className="text-xs text-[rgb(var(--muted))]">
            {t('agents.agentIdLabel')}: {agent.agent_id}
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-end">
            <div className="flex-1">
              <TextField
                label={t('remotes.name')}
                value={agentName}
                onChange={(event) => setAgentName(event.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-end">
            <div className="flex-1">
              <TextField
                label={t('agents.configurationUrlLabel')}
                hint={t('agents.configurationUrlHint')}
                value={configurationUrl}
                onChange={(event) => setConfigurationUrl(event.target.value)}
              />
            </div>
            <Button variant="secondary" onClick={fillCurrentUrl}>
              {t('agents.configurationUrlAuto')}
            </Button>
            <Button onClick={() => saveMutation.mutate()} disabled={!hasChanges || saveMutation.isPending}>
              {t('common.save')}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('agents.assignedRemotesTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          {assignedRemotes.length === 0 ? (
            <div className="text-sm text-[rgb(var(--muted))]">{t('agents.assignedRemotesEmpty')}</div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {assignedRemotes.map((remote) => (
                <button
                  key={remote.id}
                  type="button"
                  className="w-full rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] p-3 text-left shadow-[var(--shadow)] hover:shadow-[0_14px_30px_rgba(2,6,23,0.12)]"
                  onClick={() => navigate(`/remotes/${remote.id}`)}
                >
                  <div className="font-semibold">{remote.name}</div>
                  <div className="text-xs text-[rgb(var(--muted))]">#{remote.id}</div>
                </button>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
