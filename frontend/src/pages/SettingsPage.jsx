import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { getAppConfig } from '../utils/appConfig.js'
import { getHealth } from '../api/healthApi.js'
import { getSettings, updateSettings } from '../api/settingsApi.js'
import { Button } from '../components/ui/Button.jsx'
import { Modal } from '../components/ui/Modal.jsx'
import { NumberField } from '../components/ui/NumberField.jsx'
import { ErrorCallout } from '../components/ui/ErrorCallout.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'

export function SettingsPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const config = useMemo(() => getAppConfig(), [])
  const healthQuery = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: getSettings, staleTime: 60_000 })

  const irRxDevice = healthQuery.data?.ir_rx_device
  const irTxDevice = healthQuery.data?.ir_tx_device
  const deviceText = t('health.deviceLine', {
    rx: irRxDevice || t('common.notAvailable'),
    tx: irTxDevice || t('common.notAvailable'),
  })
  const debugLabel = healthQuery.data?.debug ? t('common.yes') : t('common.no')
  const writeKeyRequiredLabel = config.writeRequiresApiKey ? t('common.yes') : t('common.no')

  const [helpOpen, setHelpOpen] = useState(false)
  const [learningDirty, setLearningDirty] = useState(false)
  const [pressTakesDefault, setPressTakesDefault] = useState('')
  const [captureTimeoutMsDefault, setCaptureTimeoutMsDefault] = useState('')
  const [holdIdleTimeoutMs, setHoldIdleTimeoutMs] = useState('')
  const [aggregateRoundToUs, setAggregateRoundToUs] = useState('')
  const [aggregateMinMatchPercent, setAggregateMinMatchPercent] = useState('')

  useEffect(() => {
    if (!settingsQuery.data || learningDirty) return
    const defaults = getLearningDefaults(settingsQuery.data)
    setPressTakesDefault(String(defaults.pressTakes))
    setCaptureTimeoutMsDefault(String(defaults.captureTimeoutMs))
    setHoldIdleTimeoutMs(String(defaults.holdIdleTimeoutMs))
    setAggregateRoundToUs(String(defaults.aggregateRoundToUs))
    setAggregateMinMatchPercent(String(defaults.aggregateMinMatchPercent))
  }, [settingsQuery.data, learningDirty])

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      setLearningDirty(false)
      toast.show({ title: t('settings.learningTitle'), message: t('settings.learningSaved') })
    },
    onError: (e) => toast.show({ title: t('settings.learningTitle'), message: e?.message || t('settings.learningSaveFailed') }),
  })

  const defaults = settingsQuery.data ? getLearningDefaults(settingsQuery.data) : null
  const pressTakesValue = parseNumberInput(pressTakesDefault)
  const captureTimeoutValue = parseNumberInput(captureTimeoutMsDefault)
  const holdIdleValue = parseNumberInput(holdIdleTimeoutMs)
  const aggregateRoundValue = parseNumberInput(aggregateRoundToUs)
  const matchPercentValue = parseNumberInput(aggregateMinMatchPercent)

  const isPressTakesValid = isNumberInRange(pressTakesValue, 1, 50)
  const isCaptureTimeoutValid = isNumberInRange(captureTimeoutValue, 100, 60000)
  const isHoldIdleValid = isNumberInRange(holdIdleValue, 50, 2000)
  const isAggregateRoundValid = isNumberInRange(aggregateRoundValue, 1, 1000)
  const isMatchPercentValid = isNumberInRange(matchPercentValue, 10, 100)

  const hasInvalid =
    !isPressTakesValid ||
    !isCaptureTimeoutValid ||
    !isHoldIdleValid ||
    !isAggregateRoundValid ||
    !isMatchPercentValid

  const hasChanges = Boolean(defaults) && !hasInvalid && (
    pressTakesValue !== defaults.pressTakes ||
    captureTimeoutValue !== defaults.captureTimeoutMs ||
    holdIdleValue !== defaults.holdIdleTimeoutMs ||
    aggregateRoundValue !== defaults.aggregateRoundToUs ||
    matchPercentValue !== defaults.aggregateMinMatchPercent
  )

  const isSaving = updateMutation.isPending
  const disableLearningForm = !settingsQuery.data || isSaving

  const handleLearningChange = (setter) => (event) => {
    setLearningDirty(true)
    setter(event.target.value)
  }

  const handleSaveLearning = () => {
    if (!defaults || hasInvalid || matchPercentValue == null) return
    updateMutation.mutate({
      press_takes_default: pressTakesValue,
      capture_timeout_ms_default: captureTimeoutValue,
      hold_idle_timeout_ms: holdIdleValue,
      aggregate_round_to_us: aggregateRoundValue,
      aggregate_min_match_ratio: Number((matchPercentValue / 100).toFixed(2)),
    })
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.runtime')}</CardTitle>
          <Button variant="secondary" size="sm" onClick={() => setHelpOpen(true)}>
            {t('settings.help')}
          </Button>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('settings.baseUrl')}</div>
              <div className="font-semibold break-words">{config.publicBaseUrl}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('settings.apiBaseUrl')}</div>
              <div className="font-semibold break-words">{config.apiBaseUrl}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('health.device')}</div>
              <div className="font-semibold">{deviceText}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('health.debug')}</div>
              <div className="font-semibold">{debugLabel}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('settings.writeKeyRequired')}</div>
              <div className="font-semibold">{writeKeyRequiredLabel}</div>
            </div>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('settings.learningTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="text-sm text-[rgb(var(--muted))]">{t('settings.learningDescription')}</div>
          {settingsQuery.isError ? (
            <div className="mt-3">
              <ErrorCallout error={settingsQuery.error} />
            </div>
          ) : null}
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            <NumberField
              label={t('settings.learningPressTakesLabel')}
              hint={t('settings.learningPressTakesHint')}
              value={pressTakesDefault}
              min={1}
              max={50}
              step={1}
              disabled={disableLearningForm}
              aria-invalid={!isPressTakesValid}
              onChange={handleLearningChange(setPressTakesDefault)}
            />
            <NumberField
              label={t('settings.learningTimeoutLabel')}
              hint={t('settings.learningTimeoutHint')}
              value={captureTimeoutMsDefault}
              min={100}
              max={60000}
              step={100}
              disabled={disableLearningForm}
              aria-invalid={!isCaptureTimeoutValid}
              onChange={handleLearningChange(setCaptureTimeoutMsDefault)}
            />
            <NumberField
              label={t('settings.learningHoldIdleLabel')}
              hint={t('settings.learningHoldIdleHint')}
              value={holdIdleTimeoutMs}
              min={50}
              max={2000}
              step={50}
              disabled={disableLearningForm}
              aria-invalid={!isHoldIdleValid}
              onChange={handleLearningChange(setHoldIdleTimeoutMs)}
            />
            <NumberField
              label={t('settings.learningRoundLabel')}
              hint={t('settings.learningRoundHint')}
              value={aggregateRoundToUs}
              min={1}
              max={1000}
              step={1}
              disabled={disableLearningForm}
              aria-invalid={!isAggregateRoundValid}
              onChange={handleLearningChange(setAggregateRoundToUs)}
            />
            <NumberField
              label={t('settings.learningMatchLabel')}
              hint={t('settings.learningMatchHint')}
              value={aggregateMinMatchPercent}
              min={10}
              max={100}
              step={1}
              disabled={disableLearningForm}
              aria-invalid={!isMatchPercentValid}
              onChange={handleLearningChange(setAggregateMinMatchPercent)}
            />
          </div>
          <div className="mt-4 flex justify-end">
            <Button onClick={handleSaveLearning} disabled={disableLearningForm || hasInvalid || !hasChanges}>
              {t('common.save')}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Modal
        open={helpOpen}
        title={t('settings.help')}
        onClose={() => setHelpOpen(false)}
        footer={
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => setHelpOpen(false)}>
              {t('common.close')}
            </Button>
          </div>
        }
      >
        <div className="space-y-2 text-sm text-[rgb(var(--muted))]">
          <div>
            <div className="font-semibold text-[rgb(var(--fg))]">{t('settings.helpPublicBaseUrlTitle')}</div>
            <div>{t('settings.helpPublicBaseUrlBody')}</div>
          </div>
          <div>
            <div className="font-semibold text-[rgb(var(--fg))]">{t('settings.helpApiKeyTitle')}</div>
            <div>{t('settings.helpApiKeyBody')}</div>
          </div>
          <div>
            <div className="font-semibold text-[rgb(var(--fg))]">{t('settings.helpReverseProxyTitle')}</div>
            <div>{t('settings.helpReverseProxyBody')}</div>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function getLearningDefaults(settings) {
  // Normalize learning defaults for the UI form state.
  return {
    pressTakes: getSettingNumber(settings?.press_takes_default, 5),
    captureTimeoutMs: getSettingNumber(settings?.capture_timeout_ms_default, 3000),
    holdIdleTimeoutMs: getSettingNumber(settings?.hold_idle_timeout_ms, 300),
    aggregateRoundToUs: getSettingNumber(settings?.aggregate_round_to_us, 10),
    aggregateMinMatchPercent: Math.round(getSettingNumber(settings?.aggregate_min_match_ratio, 0.6) * 100),
  }
}

function getSettingNumber(value, fallback) {
  // Keep defaults stable when settings are missing or invalid.
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function parseNumberInput(value) {
  // Accept both empty and numeric inputs from number fields.
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function isNumberInRange(value, min, max) {
  // Guard against invalid inputs before saving.
  return typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max
}
