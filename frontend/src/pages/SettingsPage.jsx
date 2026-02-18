import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { getAppConfig } from '../utils/appConfig.js'
import { getElectronicsStatus } from '../api/statusApi.js'
import { getSettings, updateSettings } from '../api/settingsApi.js'
import { Button } from '../components/ui/Button.jsx'
import { Modal } from '../components/ui/Modal.jsx'
import { NumberField } from '../components/ui/NumberField.jsx'
import { SelectField } from '../components/ui/SelectField.jsx'
import { TextField } from '../components/ui/TextField.jsx'
import { Tooltip } from '../components/ui/Tooltip.jsx'
import { ErrorCallout } from '../components/ui/ErrorCallout.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'

export function SettingsPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const errorMapper = new ApiErrorMapper(t)
  const config = useMemo(() => getAppConfig(), [])
  const electronicsQuery = useQuery({ queryKey: ['status-electronics'], queryFn: getElectronicsStatus })
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: getSettings, staleTime: 60_000 })

  const irRxDevice = electronicsQuery.data?.ir_rx_device
  const irTxDevice = electronicsQuery.data?.ir_tx_device
  const deviceText = t('health.deviceLine', {
    rx: irRxDevice || t('common.notAvailable'),
    tx: irTxDevice || t('common.notAvailable'),
  })
  const debugLabel = electronicsQuery.data?.debug ? t('common.yes') : t('common.no')
  const writeKeyRequiredLabel = config.writeRequiresApiKey ? t('common.yes') : t('common.no')

  const [helpOpen, setHelpOpen] = useState(false)
  const [learningDirty, setLearningDirty] = useState(false)
  const [pressTakesDefault, setPressTakesDefault] = useState('')
  const [captureTimeoutMsDefault, setCaptureTimeoutMsDefault] = useState('')
  const [holdIdleTimeoutMs, setHoldIdleTimeoutMs] = useState('')
  const [aggregateRoundToUs, setAggregateRoundToUs] = useState('')
  const [aggregateMinMatchPercent, setAggregateMinMatchPercent] = useState('')
  const [hubIsAgent, setHubIsAgent] = useState(true)
  const [mqttDirty, setMqttDirty] = useState(false)
  const [mqttHost, setMqttHost] = useState('')
  const [mqttPort, setMqttPort] = useState('1883')
  const [mqttUsername, setMqttUsername] = useState('')
  const [mqttPassword, setMqttPassword] = useState('')
  const [mqttInstance, setMqttInstance] = useState('')
  const [mqttClientIdPrefix, setMqttClientIdPrefix] = useState('ir-hub')

  useEffect(() => {
    if (!settingsQuery.data || learningDirty) return
    const defaults = getLearningDefaults(settingsQuery.data)
    setPressTakesDefault(String(defaults.pressTakes))
    setCaptureTimeoutMsDefault(String(defaults.captureTimeoutMs))
    setHoldIdleTimeoutMs(String(defaults.holdIdleTimeoutMs))
    setAggregateRoundToUs(String(defaults.aggregateRoundToUs))
    setAggregateMinMatchPercent(String(defaults.aggregateMinMatchPercent))
  }, [settingsQuery.data, learningDirty])

  useEffect(() => {
    if (!settingsQuery.data) return
    setHubIsAgent(Boolean(settingsQuery.data.hub_is_agent ?? true))
  }, [settingsQuery.data])

  useEffect(() => {
    if (!settingsQuery.data || mqttDirty) return
    const defaults = getMqttDefaults(settingsQuery.data)
    setMqttHost(defaults.host)
    setMqttPort(String(defaults.port))
    setMqttUsername(defaults.username)
    setMqttInstance(defaults.instance)
    setMqttClientIdPrefix(defaults.clientIdPrefix)
    setMqttPassword('')
  }, [settingsQuery.data, mqttDirty])

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      setLearningDirty(false)
      toast.show({ title: t('settings.learningTitle'), message: t('settings.learningSaved') })
    },
    onError: (e) => toast.show({ title: t('settings.learningTitle'), message: errorMapper.getMessage(e, 'settings.learningSaveFailed') }),
  })

  const hubAgentMutation = useMutation({
    mutationFn: (value) => updateSettings({ hub_is_agent: value }),
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      setHubIsAgent(Boolean(data?.hub_is_agent ?? true))
      toast.show({ title: t('settings.agentTitle'), message: t('common.saved') })
    },
    onError: (e) => toast.show({ title: t('settings.agentTitle'), message: errorMapper.getMessage(e, 'common.failed') }),
  })

  const mqttMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      setMqttDirty(false)
      setMqttPassword('')
      toast.show({ title: t('settings.mqttTitle'), message: t('settings.mqttSaved') })
    },
    onError: (e) => toast.show({ title: t('settings.mqttTitle'), message: errorMapper.getMessage(e, 'settings.mqttSaveFailed') }),
  })

  const learningDefaults = settingsQuery.data ? getLearningDefaults(settingsQuery.data) : null
  const mqttDefaults = settingsQuery.data ? getMqttDefaults(settingsQuery.data) : null

  const pressTakesValue = parseNumberInput(pressTakesDefault)
  const captureTimeoutValue = parseNumberInput(captureTimeoutMsDefault)
  const holdIdleValue = parseNumberInput(holdIdleTimeoutMs)
  const aggregateRoundValue = parseNumberInput(aggregateRoundToUs)
  const matchPercentValue = parseNumberInput(aggregateMinMatchPercent)
  const mqttPortValue = parseNumberInput(mqttPort)

  const mqttHostValue = normalizeText(mqttHost)
  const mqttUsernameValue = normalizeText(mqttUsername)
  const mqttInstanceValue = normalizeText(mqttInstance)
  const mqttClientIdPrefixValue = normalizeText(mqttClientIdPrefix)
  const mqttPasswordValue = mqttPassword

  const isPressTakesValid = isNumberInRange(pressTakesValue, 1, 50)
  const isCaptureTimeoutValid = isNumberInRange(captureTimeoutValue, 100, 60000)
  const isHoldIdleValid = isNumberInRange(holdIdleValue, 50, 2000)
  const isAggregateRoundValid = isNumberInRange(aggregateRoundValue, 1, 1000)
  const isMatchPercentValid = isNumberInRange(matchPercentValue, 10, 100)
  const isMqttPortValid = isNumberInRange(mqttPortValue, 1, 65535)
  const isMqttInstanceValid = /^[A-Za-z0-9_-]*$/.test(mqttInstanceValue)
  const isMqttClientIdPrefixValid = /^[A-Za-z0-9-]*$/.test(mqttClientIdPrefixValue)
  const hasMqttPasswordInput = mqttPasswordValue.length > 0
  const hasMasterKey = Boolean(settingsQuery.data?.settings_master_key_configured)
  const hasMqttInvalid = !isMqttPortValid || !isMqttInstanceValid || !isMqttClientIdPrefixValid || (hasMqttPasswordInput && !hasMasterKey)

  const hasInvalid =
    !isPressTakesValid ||
    !isCaptureTimeoutValid ||
    !isHoldIdleValid ||
    !isAggregateRoundValid ||
    !isMatchPercentValid

  const hasChanges = Boolean(learningDefaults) && !hasInvalid && (
    pressTakesValue !== learningDefaults.pressTakes ||
    captureTimeoutValue !== learningDefaults.captureTimeoutMs ||
    holdIdleValue !== learningDefaults.holdIdleTimeoutMs ||
    aggregateRoundValue !== learningDefaults.aggregateRoundToUs ||
    matchPercentValue !== learningDefaults.aggregateMinMatchPercent
  )

  const hasMqttChanges = Boolean(mqttDefaults) && !hasMqttInvalid && (
    mqttHostValue !== mqttDefaults.host ||
    mqttPortValue !== mqttDefaults.port ||
    mqttUsernameValue !== mqttDefaults.username ||
    mqttInstanceValue !== mqttDefaults.instance ||
    mqttClientIdPrefixValue !== mqttDefaults.clientIdPrefix ||
    hasMqttPasswordInput
  )

  const isSaving = updateMutation.isPending
  const isSavingMqtt = mqttMutation.isPending
  const disableLearningForm = !settingsQuery.data || isSaving
  const disableMqttForm = !settingsQuery.data || isSavingMqtt
  const mqttPasswordStored = Boolean(settingsQuery.data?.mqtt_password_set)
  const showMasterKeyWarning = !hasMasterKey

  const handleLearningChange = (setter) => (event) => {
    setLearningDirty(true)
    setter(event.target.value)
  }

  const handleMqttChange = (setter) => (event) => {
    setMqttDirty(true)
    setter(event.target.value)
  }

  const handleSaveLearning = () => {
    if (!learningDefaults || hasInvalid || matchPercentValue == null) return
    updateMutation.mutate({
      press_takes_default: pressTakesValue,
      capture_timeout_ms_default: captureTimeoutValue,
      hold_idle_timeout_ms: holdIdleValue,
      aggregate_round_to_us: aggregateRoundValue,
      aggregate_min_match_ratio: Number((matchPercentValue / 100).toFixed(2)),
    })
  }

  const handleSaveMqtt = () => {
    if (!mqttDefaults || hasMqttInvalid || mqttPortValue == null) return
    const payload = {
      mqtt_host: mqttHostValue,
      mqtt_port: mqttPortValue,
      mqtt_username: mqttUsernameValue,
      mqtt_instance: mqttInstanceValue,
      mqtt_client_id_prefix: mqttClientIdPrefixValue,
    }
    if (hasMqttPasswordInput) {
      payload.mqtt_password = mqttPasswordValue
    }
    mqttMutation.mutate(payload)
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
          <CardTitle>{t('settings.agentTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="text-sm text-[rgb(var(--muted))]">{t('settings.agentDescription')}</div>
          <div className="mt-3 max-w-sm">
            <SelectField
              label={t('settings.hubIsAgentLabel')}
              hint={t('settings.hubIsAgentHint')}
              value={hubIsAgent ? 'true' : 'false'}
              onChange={(event) => {
                const nextValue = event.target.value === 'true'
                setHubIsAgent(nextValue)
                hubAgentMutation.mutate(nextValue)
              }}
              disabled={!settingsQuery.data || hubAgentMutation.isPending}
            >
              <option value="true">{t('common.yes')}</option>
              <option value="false">{t('common.no')}</option>
            </SelectField>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('settings.mqttTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="text-sm text-[rgb(var(--muted))]">{t('settings.mqttDescription')}</div>
          {showMasterKeyWarning ? (
            <div className="mt-3 rounded-xl border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-700">
              {t('settings.mqttMasterKeyMissing')}
            </div>
          ) : null}
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            <TextField
              label={t('settings.mqttHostLabel')}
              hint={t('settings.mqttHostHint')}
              value={mqttHost}
              disabled={disableMqttForm}
              onChange={handleMqttChange(setMqttHost)}
            />
            <NumberField
              label={t('settings.mqttPortLabel')}
              hint={t('settings.mqttPortHint')}
              value={mqttPort}
              min={1}
              max={65535}
              step={1}
              disabled={disableMqttForm}
              aria-invalid={!isMqttPortValid}
              onChange={handleMqttChange(setMqttPort)}
            />
            <TextField
              label={t('settings.mqttUsernameLabel')}
              hint={t('settings.mqttUsernameHint')}
              value={mqttUsername}
              disabled={disableMqttForm}
              onChange={handleMqttChange(setMqttUsername)}
            />
            <TextField
              type="password"
              label={t('settings.mqttPasswordLabel')}
              hint={mqttPasswordStored ? t('settings.mqttPasswordStoredHint') : t('settings.mqttPasswordHint')}
              value={mqttPassword}
              disabled={disableMqttForm}
              onChange={handleMqttChange(setMqttPassword)}
            />
            <TextField
              label={
                <span className="inline-flex items-center gap-2">
                  <span>{t('settings.mqttBaseTopicLabel')}</span>
                  <Tooltip label={t('settings.mqttBaseTopicHint')}>
                    <button
                      type="button"
                      aria-label={t('settings.help')}
                      className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[rgb(var(--border))] text-[10px] text-[rgb(var(--muted))] hover:text-[rgb(var(--fg))]"
                    >
                      ?
                    </button>
                  </Tooltip>
                </span>
              }
              hint={t('settings.mqttBaseTopicHint')}
              value={mqttInstance}
              disabled={disableMqttForm}
              aria-invalid={!isMqttInstanceValid}
              onChange={handleMqttChange(setMqttInstance)}
            />
            <TextField
              label={t('settings.mqttClientIdPrefixLabel')}
              hint={t('settings.mqttClientIdPrefixHint')}
              value={mqttClientIdPrefix}
              disabled={disableMqttForm}
              aria-invalid={!isMqttClientIdPrefixValid}
              onChange={handleMqttChange(setMqttClientIdPrefix)}
            />
          </div>
          <div className="mt-4 flex justify-end">
            <Button onClick={handleSaveMqtt} disabled={disableMqttForm || hasMqttInvalid || !hasMqttChanges}>
              {t('common.save')}
            </Button>
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

function getMqttDefaults(settings) {
  // Normalize MQTT settings for the UI form state.
  return {
    host: normalizeText(settings?.mqtt_host),
    port: getSettingNumber(settings?.mqtt_port, 1883),
    username: normalizeText(settings?.mqtt_username),
    instance: normalizeText(settings?.mqtt_instance),
    clientIdPrefix: normalizeText(settings?.mqtt_client_id_prefix) || 'ir-hub',
  }
}

function getSettingNumber(value, fallback) {
  // Keep defaults stable when settings are missing or invalid.
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
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
