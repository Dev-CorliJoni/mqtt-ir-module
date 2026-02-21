import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiDotsHorizontal, mdiPencilOutline, mdiPlus, mdiTrashCanOutline } from '@mdi/js'

import { deleteAgent, getAgent } from '../api/agentsApi.js'
import { createRemote, deleteRemote, listRemotes, updateRemote } from '../api/remotesApi.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { IconButton } from '../components/ui/IconButton.jsx'
import { ConfirmDialog } from '../components/ui/ConfirmDialog.jsx'
import { Drawer } from '../components/ui/Drawer.jsx'
import { Modal } from '../components/ui/Modal.jsx'
import { TextField } from '../components/ui/TextField.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'
import { AgentEditorDrawer } from '../features/agents/AgentEditorDrawer.jsx'
import { RemoteEditorDrawer } from '../features/remotes/RemoteEditorDrawer.jsx'
import { DEFAULT_REMOTE_ICON, findIconPath } from '../icons/iconRegistry.js'

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
  const [createRemoteOpen, setCreateRemoteOpen] = useState(false)
  const [newRemoteName, setNewRemoteName] = useState('')
  const [menuRemote, setMenuRemote] = useState(null)
  const [editRemote, setEditRemote] = useState(null)
  const [deleteRemoteTarget, setDeleteRemoteTarget] = useState(null)

  const handleCreateRemoteClose = () => {
    setCreateRemoteOpen(false)
    setNewRemoteName('')
  }

  const deleteAgentMutation = useMutation({
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

  const createRemoteMutation = useMutation({
    mutationFn: async () => {
      const created = await createRemote({ name: newRemoteName.trim(), icon: null })
      return updateRemote(created.id, {
        ...created,
        assigned_agent_id: agentId || null,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('remotes.create'), message: t('common.saved') })
      handleCreateRemoteClose()
    },
    onError: (error) => {
      toast.show({ title: t('remotes.create'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const deleteRemoteMutation = useMutation({
    mutationFn: (remoteId) => deleteRemote(remoteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('common.delete'), message: t('common.deleted') })
      setDeleteRemoteTarget(null)
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
          <IconButton label={t('remotes.create')} onClick={() => setCreateRemoteOpen(true)}>
            <Icon path={mdiPlus} size={1} />
          </IconButton>
        </CardHeader>
        <CardBody>
          {assignedRemotes.length === 0 ? (
            <div className="text-sm text-[rgb(var(--muted))]">{t('agents.assignedRemotesEmpty')}</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {assignedRemotes.map((remote) => (
                <div
                  key={remote.id}
                  className="group aspect-square rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] p-3 text-left shadow-[var(--shadow)] hover:shadow-[0_14px_30px_rgba(2,6,23,0.12)] cursor-pointer flex flex-col gap-3 transition-shadow"
                  onClick={() => navigate(`/remotes/${remote.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      navigate(`/remotes/${remote.id}`)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="h-12 w-12 rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] flex items-center justify-center">
                      <Icon path={findIconPath(remote.icon || DEFAULT_REMOTE_ICON)} size={1.2} />
                    </div>
                    <div onClick={(event) => event.stopPropagation()}>
                      <IconButton label={t('common.menu')} onClick={() => setMenuRemote(remote)} className="h-9 w-9 opacity-80 group-hover:opacity-100">
                        <Icon path={mdiDotsHorizontal} size={1} />
                      </IconButton>
                    </div>
                  </div>
                  <div className="mt-auto min-w-0">
                    <div className="font-semibold truncate">{remote.name}</div>
                    <div className="text-xs text-[rgb(var(--muted))]">#{remote.id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {editOpen ? <AgentEditorDrawer key={agent.agent_id} agent={agent} onClose={() => setEditOpen(false)} /> : null}
      <RemoteEditorDrawer open={Boolean(editRemote)} remote={editRemote} onClose={() => setEditRemote(null)} />

      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        body={`${agentLabel} (${agent.agent_id})`}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => deleteAgentMutation.mutate()}
      />

      <ConfirmDialog
        open={Boolean(deleteRemoteTarget)}
        title={t('remotes.deleteConfirmTitle')}
        body={t('remotes.deleteConfirmBody')}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteRemoteTarget(null)}
        onConfirm={() => {
          if (!deleteRemoteTarget) return
          deleteRemoteMutation.mutate(deleteRemoteTarget.id)
        }}
      />

      <Drawer open={Boolean(menuRemote)} title={menuRemote?.name || ''} onClose={() => setMenuRemote(null)}>
        <div className="space-y-2">
          <Button
            variant="secondary"
            className="w-full justify-start"
            onClick={() => {
              setEditRemote(menuRemote)
              setMenuRemote(null)
            }}
          >
            <Icon path={mdiPencilOutline} size={1} />
            {t('common.edit')}
          </Button>
          <Button
            variant="danger"
            className="w-full justify-start"
            onClick={() => {
              setDeleteRemoteTarget(menuRemote)
              setMenuRemote(null)
            }}
          >
            <Icon path={mdiTrashCanOutline} size={1} />
            {t('common.delete')}
          </Button>
        </div>
      </Drawer>

      <Modal
        open={createRemoteOpen}
        title={t('remotes.create')}
        onClose={handleCreateRemoteClose}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={handleCreateRemoteClose}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => createRemoteMutation.mutate()} disabled={!newRemoteName.trim() || createRemoteMutation.isPending}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <TextField label={t('remotes.name')} value={newRemoteName} onChange={(event) => setNewRemoteName(event.target.value)} />
      </Modal>
    </div>
  )
}
