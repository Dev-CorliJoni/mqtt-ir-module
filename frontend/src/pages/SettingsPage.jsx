import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { getAppConfig } from '../utils/appConfig.js'
import { getHealth } from '../api/healthApi.js'
import { Button } from '../components/ui/Button.jsx'
import { Modal } from '../components/ui/Modal.jsx'

export function SettingsPage() {
  const { t } = useTranslation()
  const config = useMemo(() => getAppConfig(), [])
  const healthQuery = useQuery({ queryKey: ['health'], queryFn: getHealth })

  const [helpOpen, setHelpOpen] = useState(false)

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
              <div className="font-semibold">{healthQuery.data?.ir_device || '—'}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('health.debug')}</div>
              <div className="font-semibold">{String(Boolean(healthQuery.data?.debug))}</div>
            </div>
            <div>
              <div className="text-xs text-[rgb(var(--muted))]">{t('settings.writeKeyRequired')}</div>
              <div className="font-semibold">{String(Boolean(config.writeRequiresApiKey))}</div>
            </div>
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
            <div className="font-semibold text-[rgb(var(--fg))]">PUBLIC_BASE_URL</div>
            <div>
              Set this in docker-compose to host the UI under a sub-path (e.g. <code>/mqtt-ir-module/</code>).
            </div>
          </div>
          <div>
            <div className="font-semibold text-[rgb(var(--fg))]">API_KEY</div>
            <div>
              If set, write endpoints require <code>X-API-Key</code>.
            </div>
          </div>
          <div>
            <div className="font-semibold text-[rgb(var(--fg))]">Reverse proxy</div>
            <div>
              Recommended: inject <code>X-API-Key</code> in the proxy. See <code>docs/reverse-proxy.md</code>.
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}