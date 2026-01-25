import React from 'react'
import { useTranslation } from 'react-i18next'
import { Modal } from '../ui/Modal.jsx'
import { Button } from '../ui/Button.jsx'
import { SelectField } from '../ui/SelectField.jsx'

export function AgentPickerModal({
  open,
  agents,
  selectedAgentId,
  onSelectAgent,
  onConfirm,
  onClose,
  isSaving,
}) {
  const { t } = useTranslation()
  const hasAgents = Array.isArray(agents) && agents.length > 0

  return (
    <Modal
      open={open}
      title={t('agents.pickerTitle')}
      onClose={onClose}
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button onClick={onConfirm} disabled={!hasAgents || !selectedAgentId || isSaving}>
            {t('common.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-3 text-sm text-[rgb(var(--muted))]">
        <div>{t('agents.pickerDescription')}</div>
        {hasAgents ? (
          <SelectField
            label={t('agents.pickerLabel')}
            hint={t('agents.pickerHint')}
            value={selectedAgentId || ''}
            onChange={(event) => onSelectAgent(event.target.value)}
          >
            <option value="" disabled>
              {t('agents.pickerPlaceholder')}
            </option>
            {agents.map((agent) => {
              const label = agent.name || agent.agent_id
              const statusLabel = agent.status === 'online' ? '' : ` (${t('agents.statusOffline')})`
              return (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {label}{statusLabel}
                </option>
              )
            })}
          </SelectField>
        ) : (
          <div>{t('agents.noneAvailable')}</div>
        )}
      </div>
    </Modal>
  )
}
