import type { HTMLAttributes, ReactNode } from 'react'
import { cx } from './utils'

interface WindowProps extends HTMLAttributes<HTMLElement> {
  title: string
  meta?: ReactNode
  actions?: ReactNode
}

export function Window({ title, meta, actions, className, children, ...props }: WindowProps) {
  return <section className={cx('ui-window', className)} {...props}><header><div><span aria-hidden="true" className="ui-window-mark" /><strong>{title}</strong>{meta && <small>{meta}</small>}</div>{actions && <div className="ui-window-actions">{actions}</div>}</header><div className="ui-window-body">{children}</div></section>
}
