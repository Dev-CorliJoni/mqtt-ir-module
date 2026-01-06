import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Drawer } from '../../components/ui/Drawer.jsx'
import { Button } from '../../components/ui/Button.jsx'
import { TextField } from '../../components/ui/TextField.jsx'
import { NumberField } from '../../components/ui/NumberField.jsx'
import { Collapse } from '../../components/ui/Collapse.jsx'
import { ErrorCallout } from '../../components/ui/ErrorCallout.jsx'
import { useToast } from '../../components/ui/ToastProvider.jsx'
import { startLearning, stopLearning, getLearningStatus, capturePress, captureHold } from '../../api/learningApi.js'

export function LearningWizard({
  open,
  remoteId,
  remoteName,
  startExtend,
  targetButton,
  existingButtons,
  onClose,
}) {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [step, setStep] = useState('press') // press -> hold -> next -> summary
  const [buttonName, setButtonName] = useState('')
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const [takes, setTakes] = useState(5)
  const [timeoutMs, setTimeoutMs] = useState(3000)
  const [holdTimeoutMs, setHoldTimeoutMs] = useState(4000)

  const [captured, setCaptured] = useState([]) // { name, press, hold }
  const [activeButtonName, setActiveButtonName] = useState(null)

  const statusQuery = useQuery({
    queryKey: ['learnStatus'],
    queryFn: getLearningStatus,
    enabled: open,
    refetchInterval: (data) => (data?.learn_enabled ? 1000 : false),
  })

  const health = queryClient.getQueryData(['health'])
  const learningActive = Boolean(health?.learn_enabled)
  const learningRemoteId = health?.learn_remote_id ?? null

  const startMutation = useMutation({
    mutationFn: async () => {
      if (learningActive && learningRemoteId && Number(learningRemoteId) !== Number(remoteId)) {
        throw new Error(`Learning is active for another remote (${health?.learn_remote_name || learningRemoteId}). Stop it first.`)
      }
      if (learningActive && Number(learningRemoteId) === Number(remoteId)) {
        return statusQuery.data
      }
      return startLearning({ remoteId, extend: Boolean(startExtend) })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (e) => toast.show({ title: t('wizard.title'), message: e?.message || 'Failed to start learning.' }),
  })

  const stopMutation = useMutation({
    mutationFn: stopLearning,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['learnStatus'] })
    },
    onError: (e) => toast.show({ title: t('wizard.title'), message: e?.message || 'Failed to stop learning.' }),
  })

  const pressMutation = useMutation({
    mutationFn: async () => {
      const nameTrim = buttonName.trim()
      const nameForPress = targetButton?.name || (nameTrim ? nameTrim : null)

      const isExisting = Boolean(nameForPress && existingButtons.some((b) => b.name === nameForPress))
      const overwrite = Boolean(!startExtend || targetButton || (startExtend && isExisting))

      return capturePress({
        remoteId,
        takes: Number(takes),
        timeoutMs: Number(timeoutMs),
        overwrite,
        buttonName: nameForPress,
      })
    },
    onSuccess: (data) => {
      const name = data?.button?.name || buttonName.trim() || 'BTN'
      setActiveButtonName(name)
      setCaptured((prev) => {
        const next = prev.filter((x) => x.name !== name)
        next.push({ name, press: true, hold: false })
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['buttons', remoteId] })
      toast.show({ title: t('wizard.capturePress'), message: `OK: ${name}` })
      setStep('hold')
    },
  })

  const holdMutation = useMutation({
    mutationFn: async () => {
      const name = activeButtonName || targetButton?.name
      if (!name) throw new Error('No active button.')

      const existing = existingButtons.find((b) => b.name === name) || null
      const overwrite = Boolean(!startExtend || targetButton || existing?.has_hold)

      return captureHold({
        remoteId,
        timeoutMs: Number(holdTimeoutMs),
        overwrite,
        buttonName: name,
      })
    },
    onSuccess: () => {
      const name = activeButtonName || targetButton?.name
      setCaptured((prev) => prev.map((x) => (x.name === name ? { ...x, hold: true } : x)))
      queryClient.invalidateQueries({ queryKey: ['buttons', remoteId] })
      toast.show({ title: t('wizard.captureHold'), message: 'OK' })
      setStep('next')
    },
  })

  useEffect(() => {
    if (!open) return
    setCaptured([])
    setActiveButtonName(targetButton?.name || null)
    setButtonName(targetButton?.name || '')
    setStep('press')
    setAdvancedOpen(false)
    startMutation.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const defaultHint = useMemo(() => {
    const idx = statusQuery.data?.next_button_index
    if (!idx) return 'BTN_0001'
    return `BTN_${String(idx).padStart(4, '0')}`
  }, [statusQuery.data?.next_button_index])

  const canClose = !learningActive || Number(learningRemoteId) !== Number(remoteId)

  // Use a single exit handler so only the stop button is explicit, while outside clicks still exit.
  const handleStopAndClose = async () => {
    if (!canClose) {
      await stopMutation.mutateAsync()
    }
    onClose()
  }

  return (
    <Drawer
      open={open}
      title={`${t('wizard.title')}: ${remoteName || `#${remoteId}`}`}
      onClose={handleStopAndClose}
      closeOnEscape={false}
    >
      <div className="space-y-4">
        {startMutation.isError ? <ErrorCallout error={startMutation.error} /> : null}

        <div className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3">
          <div className="text-sm font-semibold">{t('wizard.buttonSetup')}</div>
          <div className="mt-3">
            <TextField
              label={t('wizard.buttonName')}
              value={buttonName}
              onChange={(e) => setButtonName(e.target.value)}
              placeholder={defaultHint}
              hint={t('wizard.buttonNameHint')}
              disabled={Boolean(targetButton)}
            />
          </div>

          <div className="mt-3">
            <Collapse open={advancedOpen} onToggle={() => setAdvancedOpen((v) => !v)} title={t('common.advanced')}>
              <div className="grid grid-cols-1 gap-3">
                <NumberField label="takes" value={takes} min={1} max={50} onChange={(e) => setTakes(e.target.value)} />
                <NumberField label="timeout_ms" value={timeoutMs} min={100} max={60000} onChange={(e) => setTimeoutMs(e.target.value)} />
                <NumberField
                  label="hold_timeout_ms"
                  value={holdTimeoutMs}
                  min={100}
                  max={60000}
                  onChange={(e) => setHoldTimeoutMs(e.target.value)}
                />
              </div>
            </Collapse>
          </div>
        </div>

        {step === 'press' ? (
          <div className="space-y-2">
            <Button className="w-full" onClick={() => pressMutation.mutate()} disabled={pressMutation.isPending || startMutation.isPending}>
              {t('wizard.capturePress')}
            </Button>
            {pressMutation.isError ? <ErrorCallout error={pressMutation.error} /> : null}
          </div>
        ) : null}

        {step === 'hold' ? (
          <div className="space-y-2">
            <Button className="w-full" onClick={() => holdMutation.mutate()} disabled={holdMutation.isPending || startMutation.isPending}>
              {t('wizard.captureHold')} ({t('common.optional')})
            </Button>
            <Button className="w-full" variant="secondary" onClick={() => setStep('next')}>
              {t('wizard.skip')}
            </Button>
            {holdMutation.isError ? <ErrorCallout error={holdMutation.error} /> : null}
          </div>
        ) : null}

        {step === 'next' ? (
          <div className="space-y-2">
            <Button className="w-full" onClick={() => resetForNextButton()}>
              {t('wizard.addAnother')}
            </Button>
            <Button
              className="w-full"
              variant="secondary"
              onClick={async () => {
                await stopMutation.mutateAsync()
                setStep('summary')
              }}
            >
              {t('wizard.finish')}
            </Button>
          </div>
        ) : null}

        {step === 'summary' ? (
          <div className="space-y-3">
            <div className="font-semibold">{t('wizard.summary')}</div>
            <div className="space-y-2">
              {captured.map((x) => (
                <div key={x.name} className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3">
                  <div className="font-semibold text-sm">{x.name}</div>
                  <div className="text-xs text-[rgb(var(--muted))]">
                    press: {x.press ? 'ok' : '—'} • hold: {x.hold ? 'ok' : '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm">Status</div>
            <Button variant="secondary" size="sm" onClick={() => statusQuery.refetch()}>
              {t('common.retry')}
            </Button>
          </div>

          {statusQuery.data?.learn_enabled ? (
            <div className="mt-2 text-xs text-[rgb(var(--muted))]">
              remote: {statusQuery.data.remote_name} • extend: {String(statusQuery.data.extend)} • next: {statusQuery.data.next_button_index}
            </div>
          ) : (
            <div className="mt-2 text-xs text-[rgb(var(--muted))]">learn_enabled=false</div>
          )}

          {statusQuery.data?.logs?.length ? (
            <div className="mt-3 max-h-40 overflow-auto space-y-2">
              {statusQuery.data.logs.slice(-30).map((l, idx) => (
                <div key={`${l.timestamp}_${idx}`} className="text-[11px] text-[rgb(var(--muted))]">
                  [{l.level}] {l.message}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="flex gap-2">
          <Button
            variant="danger"
            className="w-full"
            onClick={handleStopAndClose}
            disabled={stopMutation.isPending}
          >
            {t('remote.stopLearning')}
          </Button>
        </div>
      </div>
    </Drawer>
  )

  function resetForNextButton() {
    setStep('press')
    setActiveButtonName(null)
    setButtonName('')
    setAdvancedOpen(false)
  }
}
