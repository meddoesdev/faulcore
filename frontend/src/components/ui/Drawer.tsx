import { X } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Button } from './Button'

interface DrawerProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

export function Drawer({ open, title, onClose, children }: DrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose, open])

  if (!open) return null
  return <div className="ui-drawer-layer"><button className="ui-drawer-backdrop" aria-label="Close details" onClick={onClose} /><aside className="ui-drawer" aria-label={title}><header><h2>{title}</h2><Button ref={closeRef} variant="ghost" size="icon" aria-label="Close details" title="Close details" onClick={onClose}><X size={18} /></Button></header><div>{children}</div></aside></div>
}
