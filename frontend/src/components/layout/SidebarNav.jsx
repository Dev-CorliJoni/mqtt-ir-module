import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Icon from '@mdi/react'
import { mdiHomeOutline, mdiRemoteTv, mdiCogOutline } from '@mdi/js'

function Item({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold',
          isActive ? 'bg-[rgb(var(--bg))] border border-[rgb(var(--border))]' : 'hover:bg-[rgb(var(--bg))]',
        ].join(' ')
      }
    >
      <Icon path={icon} size={1} />
      <span>{label}</span>
    </NavLink>
  )
}

export function SidebarNav() {
  const { t } = useTranslation()

  return (
    <aside className="hidden md:flex fixed left-0 top-0 bottom-0 w-64 border-r border-[rgb(var(--border))] bg-[rgb(var(--card))] p-4">
      <div className="w-full flex flex-col gap-3">
        <div className="font-bold text-lg px-2">mqtt-ir</div>
        <nav className="flex flex-col gap-2">
          <Item to="/" icon={mdiHomeOutline} label={t('nav.home')} />
          <Item to="/remotes" icon={mdiRemoteTv} label={t('nav.remotes')} />
          <Item to="/settings" icon={mdiCogOutline} label={t('nav.settings')} />
        </nav>
      </div>
    </aside>
  )
}