import {
  Activity,
  Boxes,
  ChevronsLeftRightEllipsis,
  CircleUserRound,
  Command,
  Radio,
  Search,
  ShieldCheck,
} from 'lucide-react'
import type { PropsWithChildren } from 'react'

type AppView = 'incidents' | 'command'

interface AppShellProps extends PropsWithChildren {
  view: AppView
  incidentLabel?: string
  onNavigate: (view: AppView) => void
}

export function AppShell({ view, incidentLabel, onNavigate, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="left-rail">
        <div className="brand-mark" aria-label="FaultCore RecallScope">
          <Command size={19} strokeWidth={2.4} />
          <span>FC</span>
        </div>

        <nav className="rail-nav" aria-label="Primary navigation">
          <button
            className="rail-button"
            data-active={view === 'incidents'}
            onClick={() => onNavigate('incidents')}
            aria-label="Incidents"
          >
            <Radio size={19} />
            <span>Incidents</span>
          </button>
          <button
            className="rail-button"
            data-active={view === 'command'}
            disabled={!incidentLabel}
            onClick={() => onNavigate('command')}
            aria-label="Command centre"
          >
            <Activity size={19} />
            <span>Command</span>
          </button>
          <button
            className="rail-button"
            disabled={!incidentLabel}
            onClick={() => onNavigate('command')}
            aria-label="Exposure trace graph"
          >
            <ChevronsLeftRightEllipsis size={19} />
            <span>Trace</span>
          </button>
          <button className="rail-button" disabled aria-label="Verification, available in Phase 4">
            <ShieldCheck size={19} />
            <span>Verify</span>
          </button>
        </nav>

        <div className="rail-footer" aria-label="System status">
          <span className="system-dot" />
          <span>SIM ONLINE</span>
        </div>
      </aside>

      <div className="app-frame">
        <header className="top-bar">
          <div className="top-context">
            <Boxes size={17} />
            <span>RECALLSCOPE</span>
            <span className="top-divider">/</span>
            <strong>{incidentLabel ?? 'INCIDENT INTAKE'}</strong>
          </div>
          <div className="top-actions">
            <button className="icon-button" aria-label="Search" disabled><Search size={17} /></button>
            <div className="environment-chip"><span /> Simulation environment</div>
            <CircleUserRound size={20} className="user-icon" />
          </div>
        </header>

        <div className="workspace">{children}</div>
      </div>
    </div>
  )
}
