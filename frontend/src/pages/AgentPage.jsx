import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiPencilOutline, mdiTrashCanOutline } from '@mdi/js'

import { deleteAgent, getAgent } from '../api/agentsApi.js'
import { listRemotes } from '../api/remotesApi.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { IconButton } from '../components/ui/IconButton.jsx'
import { ConfirmDialog } from '../components/ui/ConfirmDialog.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'
import { AgentEditorDrawer } from '../features/agents/AgentEditorDrawer.jsx'

export function AgentPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const errorMapper = new ApiErrorMapper(t)
  const { agentId = '' } = useParams()

  const agentQuery = useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => getAgent(agentId),
    enabled: Boolean(agentId),
  })
  const remotesQuery = useQuery({ queryKey: ['remotes'], queryFn: listRemotes })
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => deleteAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('common.delete'), message: t('common.deleted') })
      navigate('/agents')
    },
    onError: (error) => {
      toast.show({ title: t('common.delete'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const assignedRemotes = useMemo(() => {
    const remotes = remotesQuery.data || []
    return remotes.filter((remote) => String(remote.assigned_agent_id || '') === agentId)
  }, [remotesQuery.data, agentId])

  const isLoading = agentQuery.isLoading
  const hasAgent = Boolean(agentQuery.data)

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
          <CardTitle className="flex items-center gap-3">
            <span className="truncate">{agentLabel}</span>
          </CardTitle>
          <div className="flex gap-2">
            <IconButton label={t('common.edit')} onClick={() => setEditOpen(true)}>
              <Icon path={mdiPencilOutline} size={1} />
            </IconButton>
            <IconButton label={t('common.delete')} onClick={() => setDeleteOpen(true)}>
              <Icon path={mdiTrashCanOutline} size={1} />
            </IconButton>
          </div>
        </CardHeader>
        <CardBody>
          <div className="text-xs text-[rgb(var(--muted))]">
            {t('agents.agentIdLabel')}: {agent.agent_id}
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

      {editOpen ? <AgentEditorDrawer key={agent.agent_id} agent={agent} onClose={() => setEditOpen(false)} /> : null}

      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        body={`${agentLabel} (${agent.agent_id})`}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}
