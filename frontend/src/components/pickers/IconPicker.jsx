import React, { useEffect, useMemo, useState } from 'react'
import Icon from '@mdi/react'
import { useTranslation } from 'react-i18next'
import { Drawer } from '../ui/Drawer.jsx'
import { TextField } from '../ui/TextField.jsx'
import { Button } from '../ui/Button.jsx'
import { ICONS, ICON_CATEGORIES } from '../../icons/iconRegistry.js'

const DEFAULT_CATEGORY = 'All'

export function IconPicker({ open, title, initialIconKey, onClose, onSelect }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState(DEFAULT_CATEGORY)

  useEffect(() => {
    if (!open) {
      // Reset filters when the picker closes.
      setQuery('')
      setCategory(DEFAULT_CATEGORY)
    }
  }, [open])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return ICONS.filter((i) => {
      const matchesCategory = category === DEFAULT_CATEGORY ? true : i.category === category
      const matchesQuery = q ? i.label.toLowerCase().includes(q) || i.key.toLowerCase().includes(q) : true
      return matchesCategory && matchesQuery
    })
  }, [query, category])

  const categories = useMemo(() => [DEFAULT_CATEGORY, ...ICON_CATEGORIES], [])

  return (
    <Drawer
      open={open}
      title={title}
      onClose={onClose}
      footer={
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            {t('common.close')}
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        <TextField value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('common.search')} />

        <div className="flex gap-2 flex-wrap">
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              className={[
                'px-3 py-2 rounded-full text-xs font-semibold border',
                c === category ? 'border-[rgb(var(--primary))] text-[rgb(var(--primary))]' : 'border-[rgb(var(--border))] text-[rgb(var(--muted))]',
              ].join(' ')}
            >
              {c}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {filtered.map((item) => (
            <button
              key={item.key}
              type="button"
              className={[
                'rounded-2xl border p-3 text-left hover:opacity-95',
                item.key === initialIconKey ? 'border-[rgb(var(--primary))]' : 'border-[rgb(var(--border))]',
              ].join(' ')}
              onClick={() => onSelect(item.key)}
            >
              <div className="flex items-center gap-2">
                <Icon path={item.path} size={1} />
                <div className="text-xs font-semibold truncate">{item.label}</div>
              </div>
              <div className="text-[10px] text-[rgb(var(--muted))] truncate mt-1">{item.key}</div>
            </button>
          ))}
        </div>
      </div>
    </Drawer>
  )
}
