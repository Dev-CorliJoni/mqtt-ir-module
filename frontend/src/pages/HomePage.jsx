import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { listRemotes } from '../api/remotesApi.js'
import { getHealth } from '../api/healthApi.js'
import { readLocalStorage } from '../utils/storage.js'
import { useNavigate } from 'react-router-dom'
import { RemoteTile } from '../features/remotes/RemoteTile.jsx'
import { RemoteEditorDrawer } from '../features/remotes/RemoteEditorDrawer.jsx'
import { ConfirmDialog } from '../components/ui/ConfirmDialog.jsx'
import { createRemote, deleteRemote } from '../api/remotesApi.js'
import { Modal } from '../components/ui/Modal.jsx'
import { TextField } from '../components/ui/TextField.jsx'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '../components/ui/ToastProvider.jsx'

export function HomePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()

  const healthQuery = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const remotesQuery = useQuery({ queryKey: ['remotes'], queryFn: listRemotes })

  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')

  const [editRemote, setEditRemote] = useState(null)
  const [deleteRemoteTarget, setDeleteRemoteTarget] = useState(null)

  const lastOpenedId = readLocalStorage('lastOpenedRemoteId', null)

  const bestRemote = useMemo(() => {
    const remotes = remotesQuery.data || []
    if (!remotes.length) return null
    const byLastOpened = lastOpenedId ? remotes.find((r) => Number(r.id) === Number(lastOpenedId)) : null
    if (byLastOpened) return { remote: byLastOpened, label: t('home.lastRemote') }
    const byUpdated = [...remotes].sort((a, b) => Number(b.updated_at || 0) - Number(a.updated_at || 0))[0]
    return byUpdated ? { remote: byUpdated, label: t('home.fallbackRemote') } : null
  }, [remotesQuery.data, lastOpenedId, t])

  const createMutation = useMutation({
    mutationFn: () => createRemote({ name: newName.trim(), icon: null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('remotes.create'), message: 'OK' })
      setCreateOpen(false)
      setNewName('')
    },
    onError: (e) => toast.show({ title: t('remotes.create'), message: e?.message || 'Failed.' }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteRemote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('common.delete'), message: 'OK' })
      setDeleteRemoteTarget(null)
    },
    onError: (e) => toast.show({ title: t('common.delete'), message: e?.message || 'Failed.' }),
  })

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t('health.title')}</CardTitle>
          <div className="text-xs text-[rgb(var(--muted))]">
            {healthQuery.data?.ok ? t('health.online') : t('health.offline')}
          </div>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('health.device')}</div>
              <div className="font-semibold">{healthQuery.data?.ir_device || '—'}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('health.debug')}</div>
              <div className="font-semibold">{String(Boolean(healthQuery.data?.debug))}</div>
            </div>
          </div>
        </CardBody>
      </Card>

      {bestRemote?.remote ? (
        <div className="space-y-2">
          <div className="text-sm font-semibold">{bestRemote.label}</div>
          <RemoteTile
            remote={bestRemote.remote}
            onEdit={(r) => setEditRemote(r)}
            onDelete={(r) => setDeleteRemoteTarget(r)}
          />
        </div>
      ) : (
        <Card>
          <CardBody>
            <div className="text-sm text-[rgb(var(--muted))]">{t('home.noRemotes')}</div>
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Button onClick={() => navigate('/remotes')}>{t('home.goToRemotes')}</Button>
        <Button variant="secondary" onClick={() => setCreateOpen(true)}>
          {t('home.createRemote')}
        </Button>
      </div>

      <RemoteEditorDrawer open={Boolean(editRemote)} remote={editRemote} onClose={() => setEditRemote(null)} />

      <ConfirmDialog
        open={Boolean(deleteRemoteTarget)}
        title={t('remotes.deleteConfirmTitle')}
        body={t('remotes.deleteConfirmBody')}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteRemoteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteRemoteTarget.id)}
      />

      <Modal
        open={createOpen}
        title={t('remotes.create')}
        onClose={() => setCreateOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => createMutation.mutate()} disabled={!newName.trim() || createMutation.isPending}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <TextField label={t('remotes.name')} value={newName} onChange={(e) => setNewName(e.target.value)} />
      </Modal>
    </div>
  )
}