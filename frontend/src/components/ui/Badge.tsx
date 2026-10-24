import type { HTMLAttributes, ReactNode } from 'react'
import { cx } from './utils'

export type BadgeTone = 'neutral' | 'affected' | 'possible' | 'safe' | 'held' | 'transit' | 'disagreement'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  icon?: ReactNode
}

export function Badge({ tone = 'neutral', icon, className, children, ...props }: BadgeProps) {
  return <span className={cx('ui-badge', className)} data-tone={tone} {...props}>{icon && <span aria-hidden="true">{icon}</span>}{children}</span>
}
