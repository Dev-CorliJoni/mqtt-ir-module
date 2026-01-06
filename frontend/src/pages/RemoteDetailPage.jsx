import React, { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiTrashCanOutline, mdiPencilOutline, mdiMagicStaff } from '@mdi/js'

import { listRemotes, deleteRemote } from '../api/remotesApi.js'
import { listButtons, updateButton, deleteButton, sendPress, sendHold } from '../api/buttonsApi.js'
import { getHealth } from '../api/healthApi.js'
import { writeLocalStorage } from '../utils/storage.js'

import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { IconButton } from '../components/ui/IconButton.jsx'
import { ConfirmDialog } from '../components/ui/ConfirmDialog.jsx'
import { Modal } from '../components/ui/Modal.jsx'
import { TextField } from '../components/ui/TextField.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'

import { RemoteEditorDrawer } from '../features/remotes/RemoteEditorDrawer.jsx'
import { ButtonTile } from '../features/buttons/ButtonTile.jsx'
import { HoldSendDialog } from '../features/buttons/HoldSendDialog.jsx'
import { IconPicker } from '../components/pickers/IconPicker.jsx'
import { DEFAULT_BUTTON_ICON } from '../icons/iconRegistry.js'
import { LearningWizard } from '../features/learning/LearningWizard.jsx'

export function RemoteDetailPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { remoteId } = useParams()

  const numericRemoteId = Number(remoteId)

  const healthQuery = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const remotesQuery = useQuery({ queryKey: ['remotes'], queryFn: listRemotes })
  const buttonsQuery = useQuery({ queryKey: ['buttons', numericRemoteId], queryFn: () => listButtons(numericRemoteId) })

  const remote = useMemo(() => {
    const list = remotesQuery.data || []
    return list.find((r) => Number(r.id) === numericRemoteId) || null
  }, [remotesQuery.data, numericRemoteId])

  useEffect(() => {
    if (numericRemoteId) writeLocalStorage('lastOpenedRemoteId', numericRemoteId)
  }, [numericRemoteId])

  const learningActive = Boolean(healthQuery.data?.learn_enabled)
  const learningRemoteId = healthQuery.data?.learn_remote_id ?? null
  const sendingDisabled = learningActive

  const [editRemoteOpen, setEditRemoteOpen] = useState(false)
  const [deleteRemoteOpen, setDeleteRemoteOpen] = useState(false)

  const [resetWarnOpen, setResetWarnOpen] = useState(false)

  const [renameTarget, setRenameTarget] = useState(null)
  const [renameValue, setRenameValue] = useState('')

  const [iconTarget, setIconTarget] = useState(null)
  const [iconPickerOpen, setIconPickerOpen] = useState(false)

  const [deleteButtonTarget, setDeleteButtonTarget] = useState(null)

  const [holdDialogOpen, setHoldDialogOpen] = useState(false)
  const [holdTarget, setHoldTarget] = useState(null)

  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardExtend, setWizardExtend] = useState(true)
  const [wizardTargetButton, setWizardTargetButton] = useState(null)

  const deleteRemoteMutation = useMutation({
    mutationFn: () => deleteRemote(numericRemoteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('common.delete'), message: 'Remote deleted.' })
      navigate('/remotes')
    },
    onError: (e) => toast.show({ title: t('common.delete'), message: e?.message || 'Failed.' }),
  })

  const updateButtonMutation = useMutation({
    mutationFn: ({ buttonId, name, icon }) => updateButton(buttonId, { name, icon }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buttons', numericRemoteId] })
      toast.show({ title: t('common.save'), message: 'OK' })
      setRenameTarget(null)
      setIconTarget(null)
      setIconPickerOpen(false)
    },
    onError: (e) => toast.show({ title: 'Button', message: e?.message || 'Failed.' }),
  })

  const deleteButtonMutation = useMutation({
    mutationFn: (buttonId) => deleteButton(buttonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buttons', numericRemoteId] })
      toast.show({ title: t('common.delete'), message: 'OK' })
      setDeleteButtonTarget(null)
    },
    onError: (e) => toast.show({ title: t('common.delete'), message: e?.message || 'Failed.' }),
  })

  const sendPressMutation = useMutation({
    mutationFn: (buttonId) => sendPress(buttonId),
    onSuccess: () => toast.show({ title: 'Send', message: 'Press sent.' }),
    onError: (e) => toast.show({ title: 'Send', message: e?.message || 'Failed.' }),
  })

  const sendHoldMutation = useMutation({
    mutationFn: ({ buttonId, holdMs }) => sendHold(buttonId, holdMs),
    onSuccess: () => toast.show({ title: 'Send', message: 'Hold sent.' }),
    onError: (e) => toast.show({ title: 'Send', message: e?.message || 'Failed.' }),
  })

  const existingButtons = buttonsQuery.data || []

  if (!remote) {
    return (
      <Card>
        <CardBody>
          <div className="text-sm text-[rgb(var(--muted))]">{t('errors.notFoundTitle')}</div>
        </CardBody>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <span className="truncate">{remote.name}</span>
          </CardTitle>
          <div className="flex gap-2">
            <IconButton label="Edit" onClick={() => setEditRemoteOpen(true)}>
              <Icon path={mdiPencilOutline} size={1} />
            </IconButton>
            <IconButton label="Delete" onClick={() => setDeleteRemoteOpen(true)}>
              <Icon path={mdiTrashCanOutline} size={1} />
            </IconButton>
          </div>
        </CardHeader>
        <CardBody>
          <div className="text-xs text-[rgb(var(--muted))]">#{remote.id}</div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('remote.learningTitle')}</CardTitle>
          <div className="flex gap-2">
            <IconButton
              label="Wizard"
              onClick={() => {
                setWizardTargetButton(null)
                setWizardExtend(true)
                setWizardOpen(true)
              }}
            >
              <Icon path={mdiMagicStaff} size={1} />
            </IconButton>
          </div>
        </CardHeader>
        <CardBody>
          {learningActive && Number(learningRemoteId) !== Number(numericRemoteId) ? (
            <div className="text-sm text-[rgb(var(--muted))]">
              Learning is active for another remote. Stop it to start here.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Button
                onClick={() => {
                  setWizardTargetButton(null)
                  setWizardExtend(true)
                  setWizardOpen(true)
                }}
              >
                {t('remote.startAdd')}
              </Button>

              <Button
                variant="danger"
                onClick={() => {
                  setResetWarnOpen(true)
                }}
              >
                {t('remote.startReset')}
              </Button>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('remote.buttonsTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {existingButtons.map((b) => (
              <ButtonTile
                key={b.id}
                button={b}
                sendingDisabled={sendingDisabled}
                onSendPress={() => sendPressMutation.mutate(b.id)}
                onSendHold={() => {
                  setHoldTarget(b)
                  setHoldDialogOpen(true)
                }}
                onRename={() => {
                  setRenameTarget(b)
                  setRenameValue(b.name)
                }}
                onChangeIcon={() => {
                  setIconTarget(b)
                  setIconPickerOpen(true)
                }}
                onDelete={() => setDeleteButtonTarget(b)}
                onRelearn={() => {
                  setWizardTargetButton(b)
                  setWizardExtend(true)
                  setWizardOpen(true)
                }}
              />
            ))}
          </div>
        </CardBody>
      </Card>

      <RemoteEditorDrawer open={editRemoteOpen} remote={remote} onClose={() => setEditRemoteOpen(false)} />

      <ConfirmDialog
        open={deleteRemoteOpen}
        title={t('remotes.deleteConfirmTitle')}
        body={t('remotes.deleteConfirmBody')}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteRemoteOpen(false)}
        onConfirm={() => deleteRemoteMutation.mutate()}
      />

      <Modal
        open={resetWarnOpen}
        title={t('remote.startResetWarningTitle')}
        onClose={() => setResetWarnOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setResetWarnOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setResetWarnOpen(false)
                setWizardTargetButton(null)
                setWizardExtend(false)
                setWizardOpen(true)
              }}
            >
              {t('common.confirm')}
            </Button>
          </div>
        }
      >
        <p className="text-sm text-[rgb(var(--muted))]">{t('remote.startResetWarningBody')}</p>
      </Modal>

      <Modal
        open={Boolean(renameTarget)}
        title={t('button.rename')}
        onClose={() => setRenameTarget(null)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setRenameTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => updateButtonMutation.mutate({ buttonId: renameTarget.id, name: renameValue.trim(), icon: renameTarget.icon })}
              disabled={!renameValue.trim() || updateButtonMutation.isPending}
            >
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <TextField value={renameValue} onChange={(e) => setRenameValue(e.target.value)} label={t('wizard.buttonName')} />
      </Modal>

      <IconPicker
        open={iconPickerOpen}
        title={t('button.changeIcon')}
        initialIconKey={iconTarget?.icon || DEFAULT_BUTTON_ICON}
        onClose={() => setIconPickerOpen(false)}
        onSelect={(key) => {
          updateButtonMutation.mutate({ buttonId: iconTarget.id, name: iconTarget.name, icon: key })
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteButtonTarget)}
        title={t('button.deleteConfirmTitle')}
        body={t('button.deleteConfirmBody')}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteButtonTarget(null)}
        onConfirm={() => deleteButtonMutation.mutate(deleteButtonTarget.id)}
      />

      <HoldSendDialog
        open={holdDialogOpen}
        buttonName={holdTarget?.name || ''}
        defaultMs={1000}
        onClose={() => setHoldDialogOpen(false)}
        onSend={(ms) => {
          setHoldDialogOpen(false)
          sendHoldMutation.mutate({ buttonId: holdTarget.id, holdMs: ms })
        }}
      />

      <LearningWizard
        open={wizardOpen}
        remoteId={numericRemoteId}
        remoteName={remote.name}
        startExtend={wizardExtend}
        targetButton={wizardTargetButton}
        existingButtons={existingButtons}
        onClose={() => setWizardOpen(false)}
      />
    </div>
  )
}