import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cx } from './utils'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  leadingIcon?: ReactNode
  trailingIcon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({
  variant = 'primary',
  size = 'md',
  leadingIcon,
  trailingIcon,
  className,
  children,
  type = 'button',
  ...props
}, ref) {
  return (
    <button ref={ref} type={type} className={cx('ui-button', className)} data-variant={variant} data-size={size} {...props}>
      {leadingIcon && <span aria-hidden="true">{leadingIcon}</span>}
      {children}
      {trailingIcon && <span aria-hidden="true">{trailingIcon}</span>}
    </button>
  )
})
