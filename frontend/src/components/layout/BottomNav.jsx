import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiHomeOutline, mdiRemoteTv, mdiCogOutline } from '@mdi/js'

function Tab({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          'flex flex-col items-center justify-center gap-1 flex-1 h-16 cursor-pointer transition-colors hover:bg-[rgb(var(--bg))]',
          isActive ? 'text-[rgb(var(--primary))]' : 'text-[rgb(var(--muted))]',
        ].join(' ')
      }
    >
      <Icon path={icon} size={1} />
      <span className="text-[11px] font-semibold">{label}</span>
    </NavLink>
  )
}

export function BottomNav() {
  const { t } = useTranslation()

  return (
    <div className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-[rgb(var(--border))] bg-[rgb(var(--card))]">
      <div className="flex">
        <Tab to="/" icon={mdiHomeOutline} label={t('nav.home')} />
        <Tab to="/remotes" icon={mdiRemoteTv} label={t('nav.remotes')} />
        <Tab to="/settings" icon={mdiCogOutline} label={t('nav.settings')} />
      </div>
    </div>
  )
}
