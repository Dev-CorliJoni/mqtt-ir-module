import React, { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { stopLearning } from '../../api/learningApi.js'
import { Button } from '../ui/Button.jsx'
import { Modal } from '../ui/Modal.jsx'
import { useToast } from '../ui/ToastProvider.jsx'

export function LearningBar({ remoteId, remoteName, currentPath, onNavigate }) {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [confirmOpen, setConfirmOpen] = useState(false)

  const stopMutation = useMutation({
    mutationFn: stopLearning,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['learnStatus'] })
      toast.show({ title: 'Learning', message: 'Stopped.' })
    },
    onError: (e) => {
      toast.show({ title: 'Learning', message: e?.message || 'Failed to stop.' })
    },
  })

  const remoteLabel = remoteName ? `${remoteName}` : `#${remoteId}`

  return (
    <>
      <div className="rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] px-4 py-3 flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <div className="text-sm">
          <div className="font-semibold">{t('health.learningActive')}</div>
          <div className="text-xs text-[rgb(var(--muted))]">{remoteLabel}</div>
        </div>

        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => onNavigate(`/remotes/${remoteId}`)}
          >
            Open
          </Button>
          <Button variant="danger" onClick={() => setConfirmOpen(true)} disabled={stopMutation.isPending}>
            {t('remote.stopLearning')}
          </Button>
        </div>
      </div>

      <Modal
        open={confirmOpen}
        title={t('wizard.leaveWarningTitle')}
        onClose={() => setConfirmOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                setConfirmOpen(false)
                await stopMutation.mutateAsync()
              }}
            >
              {t('remote.stopLearning')}
            </Button>
          </div>
        }
      >
        <p className="text-sm text-[rgb(var(--muted))]">{t('wizard.leaveWarningBody')}</p>
      </Modal>
    </>
  )
}