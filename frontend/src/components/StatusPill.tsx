import type { PropsWithChildren } from 'react'

type StatusTone = 'confirmed' | 'possible' | 'excluded' | 'held' | 'cleared' | 'neutral'

interface StatusPillProps extends PropsWithChildren {
  tone: StatusTone
}

export function StatusPill({ tone, children }: StatusPillProps) {
  return <span className="status-pill" data-tone={tone}>{children}</span>
}

