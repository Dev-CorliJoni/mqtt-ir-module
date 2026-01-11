import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Drawer } from '../../components/ui/Drawer.jsx'
import { Button } from '../../components/ui/Button.jsx'
import { TextField } from '../../components/ui/TextField.jsx'
import { NumberField } from '../../components/ui/NumberField.jsx'
import { Collapse } from '../../components/ui/Collapse.jsx'
import { Badge } from '../../components/ui/Badge.jsx'
import { ErrorCallout } from '../../components/ui/ErrorCallout.jsx'
import { useToast } from '../../components/ui/ToastProvider.jsx'
import { startLearning, stopLearning, capturePress, captureHold } from '../../api/learningApi.js'
import { createLearningStatusSocket } from '../../api/learningStatusSocket.js'
import { ApiErrorMapper } from '../../utils/apiErrorMapper.js'

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
  const errorMapper = new ApiErrorMapper(t)

  // Wizard flow state for press -> hold -> summary.
  const [step, setStep] = useState('press') // press -> hold -> next -> summary
  const [buttonName, setButtonName] = useState('')
  const [advancedOpen, setAdvancedOpen] = useState(false)

  // Capture configuration for press/hold.
  const [takes, setTakes] = useState(5)
  const [timeoutMs, setTimeoutMs] = useState(3000)

  // Local capture progress and status pushed over WebSocket.
  const [captured, setCaptured] = useState([]) // { name, press, hold }
  const [activeButtonName, setActiveButtonName] = useState(null)
  const [learnStatus, setLearnStatus] = useState({ learn_enabled: false, logs: [] })

  const logContainerRef = useRef(null)

  // Use cached health to avoid extra polling during learning.
  const health = queryClient.getQueryData(['health'])
  const learningActive = Boolean(health?.learn_enabled)
  const learningRemoteId = health?.learn_remote_id ?? null

  // Derive log list and key for scroll-to-latest behavior.
  const statusLogs = learnStatus.logs || []
  const latestLogKey = statusLogs.length
    ? `${statusLogs[statusLogs.length - 1].timestamp}_${statusLogs[statusLogs.length - 1].level}_${statusLogs[statusLogs.length - 1].message}`
    : ''
  const currentCapture = useMemo(() => getCurrentCapture(statusLogs), [statusLogs])
  const pressTakeStates = useMemo(() => {
    if (!currentCapture || currentCapture.mode !== 'press') return []
    return buildPressTakeStates(currentCapture)
  }, [currentCapture])
  const qualityScores = useMemo(() => getQualityScores(statusLogs), [statusLogs])
  const qualityRows = useMemo(() => buildQualityRows(qualityScores), [qualityScores])
  const qualityHasAdvice = useMemo(() => qualityRows.some((row) => row.showAdvice), [qualityRows])
  const mutedSuccessStyle = { backgroundColor: 'rgb(var(--success) / 0.7)' }

  // Mutations coordinate server-side learning actions with consistent error handling.
  const startMutation = useMutation({
    mutationFn: async () => {
      if (learningActive && learningRemoteId && Number(learningRemoteId) !== Number(remoteId)) {
        const remoteLabel = health?.learn_remote_name || learningRemoteId
        throw new Error(t('wizard.errorLearningActiveOther', { remote: remoteLabel }))
      }
      if (learningActive && Number(learningRemoteId) === Number(remoteId)) {
        return learnStatus
      }
      return startLearning({ remoteId, extend: Boolean(startExtend) })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (e) => toast.show({ title: t('wizard.title'), message: errorMapper.getMessage(e, 'wizard.errorStartFailed') }),
  })

  const stopMutation = useMutation({
    mutationFn: stopLearning,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (e) => toast.show({ title: t('wizard.title'), message: errorMapper.getMessage(e, 'wizard.errorStopFailed') }),
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
      const name = data?.button?.name || buttonName.trim() || t('wizard.defaultButtonName')
      setActiveButtonName(name)
      setCaptured((prev) => {
        const next = prev.filter((x) => x.name !== name)
        next.push({ name, press: true, hold: false })
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['buttons', remoteId] })
      toast.show({ title: t('wizard.capturePress'), message: t('wizard.capturePressSuccess', { name }) })
      setStep('hold')
    },
  })

  const holdMutation = useMutation({
    mutationFn: async () => {
      const name = activeButtonName || targetButton?.name
      if (!name) throw new Error(t('wizard.errorNoActiveButton'))

      const existing = existingButtons.find((b) => b.name === name) || null
      const overwrite = Boolean(!startExtend || targetButton || existing?.has_hold)

      return captureHold({
        remoteId,
        timeoutMs: Number(timeoutMs),
        overwrite,
        buttonName: name,
      })
    },
    onSuccess: () => {
      const name = activeButtonName || targetButton?.name
      setCaptured((prev) => prev.map((x) => (x.name === name ? { ...x, hold: true } : x)))
      queryClient.invalidateQueries({ queryKey: ['buttons', remoteId] })
      toast.show({ title: t('wizard.captureHold'), message: t('wizard.captureHoldSuccess') })
      setStep('next')
    },
  })

  useEffect(() => {
    if (!open) return
    // Reset wizard state and start a learning session when opening the drawer.
    const settingsSnapshot = queryClient.getQueryData(['settings'])
    const defaultTakes = getSettingNumber(settingsSnapshot?.press_takes_default, 5)
    const defaultTimeoutMs = getSettingNumber(settingsSnapshot?.capture_timeout_ms_default, 3000)
    setCaptured([])
    setActiveButtonName(targetButton?.name || null)
    setButtonName(targetButton?.name || '')
    setLearnStatus({ learn_enabled: false, logs: [] })
    setStep('press')
    setAdvancedOpen(false)
    setTakes(defaultTakes)
    setTimeoutMs(defaultTimeoutMs)
    startMutation.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (open) return
    // Clear wizard state when the drawer closes to avoid stale data.
    setStep('press')
    setButtonName('')
    setAdvancedOpen(false)
    setTakes(5)
    setTimeoutMs(3000)
    setCaptured([])
    setActiveButtonName(null)
    setLearnStatus({ learn_enabled: false, logs: [] })
  }, [open])

  useEffect(() => {
    if (!open) return
    // Keep a single WebSocket open while the drawer is active.
    let isActive = true
    const socket = createLearningStatusSocket({
      onMessage: (payload) => {
        if (isActive) setLearnStatus(payload)
      },
    })

    return () => {
      isActive = false
      socket.close()
    }
  }, [open])

  // Keep logs pinned to the newest entry when new logs arrive.
  useEffect(() => {
    if (!open) return
    if (!latestLogKey) return
    if (!logContainerRef.current) return
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
  }, [open, latestLogKey])

  // Suggest the next auto-generated button name while learning.
  const defaultHint = useMemo(() => {
    const idx = learnStatus.next_button_index
    const prefix = t('wizard.defaultButtonPrefix')
    if (!idx) return `${prefix}_0001`
    return `${prefix}_${String(idx).padStart(4, '0')}`
  }, [learnStatus.next_button_index, t])

  const canClose = !learningActive || Number(learningRemoteId) !== Number(remoteId)

  // Use a single exit handler so closing the drawer stops learning when needed.
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
                <NumberField
                  label={t('wizard.takesLabel')}
                  hint={t('wizard.takesHint')}
                  value={takes}
                  min={1}
                  max={50}
                  onChange={(e) => setTakes(e.target.value)}
                />
                <NumberField
                  label={t('wizard.timeoutLabel')}
                  hint={t('wizard.timeoutHint')}
                  value={timeoutMs}
                  min={100}
                  max={60000}
                  onChange={(e) => setTimeoutMs(e.target.value)}
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
                    {t('wizard.summaryPress')}: {x.press ? t('wizard.summaryOk') : t('wizard.summaryMissing')} • {t('wizard.summaryHold')}:{' '}
                    {x.hold ? t('wizard.summaryOk') : t('wizard.summaryMissing')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {step !== 'summary' ? (
          <div className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3">
            <div className="flex items-center justify-between">
              <div className="font-semibold text-sm">{t('wizard.statusTitle')}</div>
            </div>

            {learnStatus?.learn_enabled ? null : (
              <div className="mt-2 text-xs text-[rgb(var(--muted))]">{t('wizard.statusInactive')}</div>
            )}

            {currentCapture ? (
              <div className="mt-3 rounded-lg border border-[rgb(var(--border))] bg-[rgb(var(--card))] p-2">
                <div className="text-xs font-semibold">{t('wizard.captureProgressTitle')}</div>
                <div className="mt-1 text-xs text-[rgb(var(--muted))]">
                  {currentCapture.mode === 'press' ? t('wizard.captureProgressPress') : t('wizard.captureProgressHold')}
                  {currentCapture.buttonName ? ` • ${currentCapture.buttonName}` : ''}
                </div>

                {currentCapture.mode === 'press' ? (
                  <div className="mt-2 grid gap-2">
                    {pressTakeStates.map((take) => (
                      <div key={take.index} className="flex items-center justify-between text-xs">
                        <div>{t('wizard.takeLabel', { index: take.index })}</div>
                        <Badge variant={take.variant} style={take.variant === 'success' ? mutedSuccessStyle : undefined} className="gap-1">
                          {take.status === 'captured' ? <CheckIcon /> : null}
                          {t(take.labelKey)}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <Badge
                      variant={currentCapture.finished ? 'success' : currentCapture.waiting ? 'warning' : 'neutral'}
                      style={currentCapture.finished ? mutedSuccessStyle : undefined}
                      className="gap-1"
                    >
                      {currentCapture.finished ? <CheckIcon /> : null}
                      {currentCapture.finished ? t('wizard.takeStatusCaptured') : t('wizard.takeStatusWaiting')}
                    </Badge>
                  </div>
                )}
              </div>
            ) : null}

            {qualityRows.length ? (
              <div className="mt-3 rounded-lg border border-[rgb(var(--border))] bg-[rgb(var(--card))] p-2">
                <div className="text-xs font-semibold">{t('wizard.qualityTitle')}</div>
                <div className="mt-2 grid gap-2 text-xs">
                  {qualityRows.map((row) => (
                    <div key={row.key} className="flex items-center justify-between">
                      <div>{t(row.labelKey)}</div>
                      <div className="flex items-center gap-2">
                        <Badge variant={row.variant} style={row.variant === 'success' ? mutedSuccessStyle : undefined} className="gap-1">
                          {row.variant === 'success' ? <CheckIcon /> : null}
                          {t(row.qualityLabelKey)}
                        </Badge>
                        <span>{t('wizard.qualityScore', { score: formatQualityScore(row.score) })}</span>
                      </div>
                    </div>
                  ))}
                </div>
                {qualityHasAdvice ? (
                  <div className="mt-2 text-[11px] text-[rgb(var(--warning))]">
                    {t('wizard.qualityAdvice')}
                  </div>
                ) : null}
              </div>
            ) : null}

            {statusLogs.length ? (
              <div ref={logContainerRef} className="mt-3 max-h-40 overflow-auto space-y-2">
                {statusLogs.slice(-30).map((l, idx) => {
                  return (
                    <div key={`${l.timestamp}_${idx}`} className="text-[11px] text-[rgb(var(--muted))]">
                      {formatLogTime(l.timestamp)} [{l.level}] {l.message}
                    </div>
                  )
                })}
              </div>
            ) : null}
          </div>
        ) : null}
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

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className="h-3 w-3"
      fill="currentColor"
    >
      <path d="M16.704 5.296a1 1 0 0 1 0 1.414l-7.5 7.5a1 1 0 0 1-1.414 0l-3.5-3.5a1 1 0 1 1 1.414-1.414l2.793 2.793 6.793-6.793a1 1 0 0 1 1.414 0z" />
    </svg>
  )
}

function formatLogTime(timestampSeconds) {
  // Convert epoch seconds to local HH:mm:ss to keep logs compact.
  if (!Number.isFinite(timestampSeconds)) return ''
  const date = new Date(timestampSeconds * 1000)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

function getCurrentCapture(logs) {
  // Inspect the latest capture-related log group to infer current capture state.
  if (!Array.isArray(logs) || !logs.length) return null

  const startIndex = findLastIndex(logs, (entry) =>
    entry?.message === 'Capture press started' || entry?.message === 'Capture hold started'
  )
  if (startIndex < 0) return null

  const startEntry = logs[startIndex]
  const slice = logs.slice(startIndex)

  if (startEntry.message === 'Capture press started') {
    const totalTakes = toNumber(startEntry?.data?.takes)
    const buttonName = toStringValue(startEntry?.data?.button_name)
    let waitingTake = null
    const capturedTakes = []
    let finished = false

    for (const entry of slice) {
      if (entry?.message === 'Waiting for IR press') {
        waitingTake = toNumber(entry?.data?.take)
      }
      if (entry?.message === 'Captured press take') {
        const takeNumber = toNumber(entry?.data?.take)
        if (takeNumber) capturedTakes.push(takeNumber)
      }
      if (entry?.message === 'Capture press finished') {
        finished = true
      }
    }

    return {
      mode: 'press',
      buttonName,
      totalTakes,
      waitingTake,
      capturedTakes,
      finished,
    }
  }

  if (startEntry.message === 'Capture hold started') {
    let finished = false
    let waiting = false
    for (const entry of slice) {
      if (entry?.message === 'Waiting for IR hold (initial frame)') {
        waiting = true
      }
      if (entry?.message === 'Capture hold finished') {
        finished = true
      }
    }
    return {
      mode: 'hold',
      buttonName: null,
      finished,
      waiting,
    }
  }

  return null
}

function buildPressTakeStates(capture) {
  // Build per-take UI status from the most recent press capture logs.
  const totalTakes = Math.max(0, toNumber(capture.totalTakes))
  const capturedSet = new Set((capture.capturedTakes || []).filter(Boolean))
  const waitingTake = toNumber(capture.waitingTake)

  const states = []
  for (let i = 1; i <= totalTakes; i += 1) {
    let status = 'pending'
    if (capturedSet.has(i)) status = 'captured'
    else if (waitingTake === i) status = 'waiting'
    states.push({
      index: i,
      status,
      labelKey: status === 'captured'
        ? 'wizard.takeStatusCaptured'
        : status === 'waiting'
          ? 'wizard.takeStatusWaiting'
          : 'wizard.takeStatusPending',
      variant: status === 'captured' ? 'success' : status === 'waiting' ? 'warning' : 'neutral',
    })
  }
  return states
}

function getQualityScores(logs) {
  // Extract the latest press/hold quality scores from capture completion logs.
  if (!Array.isArray(logs) || !logs.length) return { press: null, hold: null }

  let press = null
  let hold = null

  for (let i = logs.length - 1; i >= 0; i -= 1) {
    const entry = logs[i]
    if (!press && entry?.message === 'Capture press finished') {
      const rawScore = entry?.data?.quality
      if (rawScore != null) {
        const score = Number(rawScore)
        if (Number.isFinite(score)) press = { score }
      }
    }
    if (!hold && entry?.message === 'Capture hold finished') {
      const rawScore = entry?.data?.quality
      if (rawScore != null) {
        const score = Number(rawScore)
        if (Number.isFinite(score)) hold = { score }
      }
    }
    if (press && hold) break
  }

  return { press, hold }
}

function buildQualityRows(scores) {
  // Convert quality scores into UI rows for press/hold.
  if (!scores) return []
  const rows = []
  if (scores.press) {
    const row = buildQualityRow({ key: 'press', labelKey: 'wizard.qualityPress', score: scores.press.score })
    if (row) rows.push(row)
  }
  if (scores.hold) {
    const row = buildQualityRow({ key: 'hold', labelKey: 'wizard.qualityHold', score: scores.hold.score })
    if (row) rows.push(row)
  }
  return rows
}

function buildQualityRow({ key, labelKey, score }) {
  const summary = getQualitySummary(score)
  if (!summary) return null
  return {
    key,
    labelKey,
    score,
    qualityLabelKey: summary.qualityLabelKey,
    variant: summary.variant,
    showAdvice: summary.showAdvice,
  }
}

function getQualitySummary(score) {
  // Map the quality score to a badge style and optional guidance text.
  if (!Number.isFinite(score)) return null
  if (score >= 0.85) {
    return { qualityLabelKey: 'wizard.qualityGood', variant: 'success', showAdvice: false }
  }
  if (score >= 0.7) {
    return { qualityLabelKey: 'wizard.qualityOk', variant: 'warning', showAdvice: false }
  }
  return { qualityLabelKey: 'wizard.qualityLow', variant: 'danger', showAdvice: true }
}

function formatQualityScore(score) {
  // Keep a stable two-decimal quality display.
  if (!Number.isFinite(score)) return '0.00'
  return score.toFixed(2)
}

function toNumber(value) {
  // Normalize mixed data values into a usable number.
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function toStringValue(value) {
  // Normalize mixed data values into a display-safe string.
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number') return String(value)
  return ''
}

function getSettingNumber(value, fallback) {
  // Allow settings defaults to safely fall back when missing or invalid.
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function findLastIndex(items, predicate) {
  // Provide findLastIndex support without requiring newer runtime helpers.
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (predicate(items[i], i)) return i
  }
  return -1
}
