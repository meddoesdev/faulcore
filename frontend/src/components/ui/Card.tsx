import type { HTMLAttributes } from 'react'
import { cx } from './utils'

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: 'article' | 'section' | 'div'
  tone?: 'plain' | 'sunk' | 'dark'
}

export function Card({ as: Element = 'article', tone = 'plain', className, ...props }: CardProps) {
  return <Element className={cx('ui-card', className)} data-tone={tone} {...props} />
}
