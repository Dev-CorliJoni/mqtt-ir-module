import React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { getSettings, updateSettings } from '../../api/settingsApi.js'
import { IconButton } from '../ui/IconButton.jsx'
import { Drawer } from '../ui/Drawer.jsx'
import { Button } from '../ui/Button.jsx'
import { useToast } from '../ui/ToastProvider.jsx'

const LANGUAGES = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'pt-PT', label: 'Português (PT)', flag: '🇵🇹' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'zh-CN', label: '中文 (简体)', flag: '🇨🇳' },
  { code: 'hi', label: 'हिन्दी', flag: '🇮🇳' },
]

export function LanguagePicker() {
  const { t } = useTranslation()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [open, setOpen] = React.useState(false)

  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const current = settingsQuery.data?.language || 'en'
  const currentMeta = LANGUAGES.find((l) => l.code === current) || LANGUAGES[0]

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      toast.show({ title: t('settings.language'), message: 'Saved.' })
    },
    onError: (e) => toast.show({ title: t('settings.language'), message: e?.message || 'Failed.' }),
  })

  return (
    <>
      <IconButton label={t('settings.language')} onClick={() => setOpen(true)}>
        <span className="text-lg">{currentMeta.flag}</span>
      </IconButton>

      <Drawer
        open={open}
        title={t('settings.language')}
        onClose={() => setOpen(false)}
        footer={
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {t('common.close')}
            </Button>
          </div>
        }
      >
        <div className="space-y-2">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              className={[
                'w-full flex items-center justify-between rounded-xl border px-3 py-3 text-sm font-semibold',
                lang.code === current ? 'border-[rgb(var(--primary))]' : 'border-[rgb(var(--border))]',
              ].join(' ')}
              onClick={() => {
                updateMutation.mutate({ language: lang.code, theme: settingsQuery.data?.theme })
              }}
            >
              <span className="flex items-center gap-3">
                <span className="text-lg">{lang.flag}</span>
                <span>{lang.label}</span>
              </span>
              <span className="text-xs text-[rgb(var(--muted))]">{lang.code}</span>
            </button>
          ))}
        </div>
      </Drawer>
    </>
  )
}