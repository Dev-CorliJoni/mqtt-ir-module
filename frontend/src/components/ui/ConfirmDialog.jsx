import React from 'react'
import { useTranslation } from 'react-i18next'
import { Modal } from './Modal.jsx'
import { Button } from './Button.jsx'

export function ConfirmDialog({ open, title, body, confirmText, confirmVariant = 'danger', onConfirm, onCancel }) {
  const { t } = useTranslation()

  return (
    <Modal
      open={open}
      title={title}
      onClose={onCancel}
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onCancel}>
            {t('common.cancel')}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm}>
            {confirmText || t('common.confirm')}
          </Button>
        </div>
      }
    >
      <p className="text-sm text-[rgb(var(--muted))]">{body}</p>
    </Modal>
  )
}
