import type { ReactNode } from 'react'

interface StatTileProps {
  label: string
  value: ReactNode
  detail?: ReactNode
  icon?: ReactNode
  tone?: 'default' | 'good' | 'warning' | 'critical'
}

export function StatTile({ label, value, detail, icon, tone = 'default' }: StatTileProps) {
  return <div className="ui-stat" data-tone={tone}><div>{icon && <span aria-hidden="true">{icon}</span>}<span>{label}</span></div><strong>{value}</strong>{detail && <small>{detail}</small>}</div>
}
