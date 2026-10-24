import type { HTMLAttributes } from 'react'
import { cx } from './utils'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('ui-skeleton', className)} aria-hidden="true" {...props} />
}
