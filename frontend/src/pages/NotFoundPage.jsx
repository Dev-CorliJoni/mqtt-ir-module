import React from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardBody } from '../components/ui/Card.jsx'

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardBody>
        <div className="text-sm">{t('errors.notFoundTitle')}</div>
      </CardBody>
    </Card>
  )
}
