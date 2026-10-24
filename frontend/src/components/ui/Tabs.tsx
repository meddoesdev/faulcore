import type { ReactNode } from 'react'

export interface TabOption<Value extends string> {
  value: Value
  label: string
  icon?: ReactNode
}

interface TabsProps<Value extends string> {
  label: string
  value: Value
  options: Array<TabOption<Value>>
  onChange: (value: Value) => void
  disabled?: boolean
}

export function Tabs<Value extends string>({ label, value, options, onChange, disabled }: TabsProps<Value>) {
  return <div className="ui-tabs" role="tablist" aria-label={label}>{options.map((option) => <button key={option.value} role="tab" aria-selected={option.value === value} disabled={disabled} onClick={() => onChange(option.value)}>{option.icon && <span aria-hidden="true">{option.icon}</span>}{option.label}</button>)}</div>
}
