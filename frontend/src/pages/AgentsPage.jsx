import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { deleteAgent, listAgents } from '../api/agentsApi.js'
import { getMqttStatus } from '../api/statusApi.js'
import { acceptPairing, closePairing, getPairingStatus, openPairing } from '../api/pairingApi.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ConfirmDialog } from '../components/ui/ConfirmDialog.jsx'
import { useToast } from '../components/ui/ToastProvider.jsx'
import { ApiErrorMapper } from '../utils/apiErrorMapper.js'
import { AgentTile } from '../features/agents/AgentTile.jsx'
import { AgentEditorDrawer } from '../features/agents/AgentEditorDrawer.jsx'

export function AgentsPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()
  const errorMapper = new ApiErrorMapper(t)
  const [editTarget, setEditTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [nowMs, setNowMs] = useState(() => Date.now())

  useEffect(() => {
    const interval = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [])

  const mqttQuery = useQuery({
    queryKey: ['status-mqtt'],
    queryFn: getMqttStatus,
    refetchInterval: 5000,
  })
  const pairingQuery = useQuery({
    queryKey: ['status-pairing'],
    queryFn: getPairingStatus,
    refetchInterval: 1000,
  })
  const agentsQuery = useQuery({
    queryKey: ['agents'],
    queryFn: listAgents,
    refetchInterval: 1000,
  })

  const openPairingMutation = useMutation({
    mutationFn: openPairing,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status-pairing'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
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
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.show({ title: t('agents.pairingTitle'), message: t('agents.pairingClosed') })
    },
    onError: (error) => {
      toast.show({ title: t('agents.pairingTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const acceptPairingMutation = useMutation({
    mutationFn: (agentId) => acceptPairing(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status-pairing'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.show({ title: t('agents.pairingTitle'), message: t('common.saved') })
    },
    onError: (error) => {
      toast.show({ title: t('agents.pairingTitle'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const deleteAgentMutation = useMutation({
    mutationFn: (agentId) => deleteAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['remotes'] })
      toast.show({ title: t('common.delete'), message: t('common.deleted') })
      setDeleteTarget(null)
    },
    onError: (error) => {
      toast.show({ title: t('common.delete'), message: errorMapper.getMessage(error, 'common.failed') })
    },
  })

  const mqttConnected = Boolean(mqttQuery.data?.connected)
  const mqttConfigured = Boolean(mqttQuery.data?.configured)
  const pairingOpen = Boolean(pairingQuery.data?.open)
  const pairingExpiresAt = Number(pairingQuery.data?.expires_at || 0)
  const agents = useMemo(() => {
    const list = agentsQuery.data || []
    return [...list].sort((a, b) => {
      const aPending = Boolean(a.pending)
      const bPending = Boolean(b.pending)
      if (aPending !== bPending) return aPending ? -1 : 1
      return String(a.name || a.agent_id).localeCompare(String(b.name || b.agent_id))
    })
  }, [agentsQuery.data])

  const pairingStateText = useMemo(() => {
    if (!mqttConfigured) return t('agents.pairingRequiresMqtt')
    if (!mqttConnected) return t('agents.pairingMqttDisconnected')
    if (!pairingOpen) return t('agents.pairingClosedState')
    if (!pairingExpiresAt) return t('agents.pairingOpenState')
    const secondsLeft = Math.max(0, Math.ceil((pairingExpiresAt * 1000 - nowMs) / 1000))
    const minutes = Math.floor(secondsLeft / 60)
    const seconds = secondsLeft % 60
    const countdown = `${minutes}:${String(seconds).padStart(2, '0')}`
    return t('agents.pairingOpenWithSeconds', { seconds: countdown })
  }, [mqttConfigured, mqttConnected, pairingOpen, pairingExpiresAt, nowMs, t])

  const pairingDisabled = !mqttConfigured || !mqttConnected
  const actionPending =
    openPairingMutation.isPending ||
    closePairingMutation.isPending ||
    acceptPairingMutation.isPending ||
    deleteAgentMutation.isPending

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
              disabled={pairingDisabled || pairingOpen || actionPending}
            >
              {t('agents.startPairing')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => closePairingMutation.mutate()}
              disabled={pairingDisabled || !pairingOpen || actionPending}
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
                <AgentTile
                  key={agent.agent_id}
                  agent={agent}
                  onAccept={(target) => acceptPairingMutation.mutate(target.agent_id)}
                  onEdit={(target) => setEditTarget(target)}
                  onDelete={(target) => setDeleteTarget(target)}
                />
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {editTarget ? <AgentEditorDrawer key={editTarget.agent_id} agent={editTarget} onClose={() => setEditTarget(null)} /> : null}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={t('common.delete')}
        body={deleteTarget ? `${deleteTarget.name || deleteTarget.agent_id} (${deleteTarget.agent_id})` : ''}
        confirmText={t('common.delete')}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (!deleteTarget) return
          deleteAgentMutation.mutate(deleteTarget.agent_id)
        }}
      />
    </div>
  )
}
