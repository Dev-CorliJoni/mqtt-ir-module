import React, { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiImageEditOutline } from '@mdi/js'

import { Drawer } from '../../components/ui/Drawer.jsx'
import { TextField } from '../../components/ui/TextField.jsx'
import { NumberField } from '../../components/ui/NumberField.jsx'
import { Collapse } from '../../components/ui/Collapse.jsx'
import { Button } from '../../components/ui/Button.jsx'
import { IconButton } from '../../components/ui/IconButton.jsx'
import { IconPicker } from '../../components/pickers/IconPicker.jsx'
import { updateRemote } from '../../api/remotesApi.js'
import { DEFAULT_REMOTE_ICON } from '../../icons/iconRegistry.js'
import { useToast } from '../../components/ui/ToastProvider.jsx'

export function RemoteEditorDrawer({ open, remote, onClose }) {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [icon, setIcon] = useState(null)
  const [carrierHz, setCarrierHz] = useState('')
  const [dutyCycle, setDutyCycle] = useState('')
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const [iconPickerOpen, setIconPickerOpen] = useState(false)

  useEffect(() => {
    if (!open) {
      // Reset form state when the drawer closes to avoid stale edits.
      setName('')
      setIcon(null)
      setCarrierHz('')
      setDutyCycle('')
      setAdvancedOpen(false)
      setIconPickerOpen(false)
      return
    }
    if (!remote) return
    setName(remote.name || '')
    setIcon(remote.icon ?? null)
    setCarrierHz(remote.carrier_hz ?? '')
    setDutyCycle(remote.duty_cycle ?? '')
    setAdvancedOpen(false)
  }, [open, remote])

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...remote,
        name: name.trim(),
        icon: icon ?? null,
        carrier_hz: carrierHz === '' ? null : Number(carrierHz),
        duty_cycle: dutyCycle === '' ? null : Number(dutyCycle),
      }
      return updateRemote(remote.id, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      queryClient.invalidateQueries({ queryKey: ['buttons', remote.id] })
      toast.show({ title: t('common.save'), message: t('common.saved') })
      onClose()
    },
    onError: (e) => toast.show({ title: t('remote.title'), message: e?.message || t('common.failed') }),
  })

  if (!remote) return null

  return (
    <>
      <Drawer
        open={open}
        title={`${t('common.edit')}: ${remote.name}`}
        onClose={onClose}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !name.trim()}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold">{t('remotes.name')}</div>
            <IconButton label={t('common.icon')} onClick={() => setIconPickerOpen(true)}>
              <Icon path={mdiImageEditOutline} size={1} />
            </IconButton>
          </div>

          <TextField value={name} onChange={(e) => setName(e.target.value)} placeholder={t('remotes.name')} />

          <Collapse open={advancedOpen} onToggle={() => setAdvancedOpen((v) => !v)} title={t('common.advanced')}>
            <div className="grid grid-cols-1 gap-3">
              <NumberField
                label={t('remote.carrierHzLabel')}
                hint={t('remote.carrierHzHint')}
                value={carrierHz}
                onChange={(e) => setCarrierHz(e.target.value)}
                placeholder="38000"
              />
              <NumberField
                label={t('remote.dutyCycleLabel')}
                hint={t('remote.dutyCycleHint')}
                value={dutyCycle}
                onChange={(e) => setDutyCycle(e.target.value)}
                placeholder="33"
              />
            </div>
          </Collapse>
        </div>
      </Drawer>

      <IconPicker
        open={iconPickerOpen}
        title={t('remote.iconTitle')}
        initialIconKey={icon || DEFAULT_REMOTE_ICON}
        onClose={() => setIconPickerOpen(false)}
        onSelect={(key) => {
          setIcon(key)
          setIconPickerOpen(false)
        }}
      />
    </>
  )
}
