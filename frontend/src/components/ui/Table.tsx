import type { HTMLAttributes, TableHTMLAttributes } from 'react'
import { cx } from './utils'

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <div className="ui-table-wrap"><table className={cx('ui-table', className)} {...props} /></div>
}

export function TableEmpty({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return <td className={cx('ui-table-empty', className)} {...props} />
}
