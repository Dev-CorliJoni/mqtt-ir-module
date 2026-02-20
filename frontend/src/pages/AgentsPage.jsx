import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { listAgents } from '../api/agentsApi.js'
import { getMqttStatus } from '../api/statusApi.js'
import { closePairing, getPairingStatus, openPairing } from '../api/pairingApi.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'

export function AgentsPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const errorMapper = new ApiErrorMapper(t)

  const mqttQuery = useQuery({
    queryKey: ['status-mqtt'],
    queryFn: getMqttStatus,
    refetchInterval: 5000,
  })
  const pairingQuery = useQuery({
    queryKey: ['status-pairing'],
    queryFn: getPairingStatus,
    refetchInterval: 2000,
  })
  const agentsQuery = useQuery({ queryKey: ['agents'], queryFn: listAgents, staleTime: 10_000 })

  const openPairingMutation = useMutation({
    mutationFn: () => openPairing(300),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status-pairing'] })
      toast.show({ title: t('agents.pairingTitle'), message: t('agents.pairingOpened') })
    },
    onError: (error) => {
      toast.show({ title: t('agents.pairingTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const closePairingMutation = useMutation({
    mutationFn: closePairing,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status-pairing'] })
      toast.show({ title: t('agents.pairingTitle'), message: t('agents.pairingClosed') })
    },
    onError: (error) => {
      toast.show({ title: t('agents.pairingTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const mqttConnected = Boolean(mqttQuery.data?.connected)
  const mqttConfigured = Boolean(mqttQuery.data?.configured)
  const pairingOpen = Boolean(pairingQuery.data?.open)
  const pairingExpiresAt = Number(pairingQuery.data?.expires_at || 0)
  const agents = agentsQuery.data || []

  const pairingStateText = useMemo(() => {
    if (!mqttConfigured) return t('agents.pairingRequiresMqtt')
    if (!mqttConnected) return t('agents.pairingMqttDisconnected')
    if (!pairingOpen) return t('agents.pairingClosedState')
    if (!pairingExpiresAt) return t('agents.pairingOpenState')
    const msLeft = Math.max(0, Math.round((pairingExpiresAt * 1000 - Date.now()) / 1000))
    return t('agents.pairingOpenWithSeconds', { seconds: msLeft })
  }, [mqttConfigured, mqttConnected, pairingOpen, pairingExpiresAt, t])

  const pairingDisabled = !mqttConfigured || !mqttConnected

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t('agents.pairingTitle')}</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="text-sm text-[rgb(var(--muted))]">{pairingStateText}</div>
          {mqttQuery.data?.last_error ? (
            <div className="text-sm text-red-600">{mqttQuery.data.last_error}</div>
          ) : null}
          {pairingDisabled ? (
            <div className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg))] p-3 text-sm">
              <div>{t('agents.pairingDisabledHint')}</div>
              <div className="mt-2">
                <Link to="/settings" className="underline">{t('agents.openSettings')}</Link>
              </div>
            </div>
          ) : null}
          <div className="flex gap-2">
            <Button
              onClick={() => openPairingMutation.mutate()}
              disabled={pairingDisabled || pairingOpen || openPairingMutation.isPending || closePairingMutation.isPending}
            >
              {t('agents.startPairing')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => closePairingMutation.mutate()}
              disabled={pairingDisabled || !pairingOpen || openPairingMutation.isPending || closePairingMutation.isPending}
            >
              {t('agents.stopPairing')}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('agents.registeredAgentsTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          {agents.length === 0 ? (
            <div className="text-sm text-[rgb(var(--muted))]">{t('agents.noAgentsRegistered')}</div>
          ) : (
            <div className="space-y-2">
              {agents.map((agent) => (
                <div
                  key={agent.agent_id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--card))] px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{agent.name || agent.agent_id}</div>
                    <div className="truncate text-xs text-[rgb(var(--muted))]">{agent.agent_id}</div>
                  </div>
                  <Link
                    to={`/agent/${agent.agent_id}`}
                    className="rounded-lg border border-[rgb(var(--border))] px-2 py-1 text-xs hover:bg-[rgb(var(--bg))]"
                  >
                    {t('agents.openAgentPage')}
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
