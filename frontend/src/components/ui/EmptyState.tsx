import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return <div className="ui-empty"><span aria-hidden="true">{icon}</span><div><strong>{title}</strong><p>{description}</p></div>{action}</div>
}
