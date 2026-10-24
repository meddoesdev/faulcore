import {
  Activity,
  GitBranch,
  ListChecks,
  RadioTower,
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
  const navigateTo = (target: 'command' | 'graph' | 'verification') => {
    onNavigate('command')
    if (target === 'graph') document.querySelector('.exposure-panel')?.scrollIntoView({ behavior: 'smooth' })
    if (target === 'verification') document.getElementById('verification-heading')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="rs-shell">
      <a className="rs-skip-link" href="#main-content">Skip to incident workspace</a>
      <header className="rs-topbar">
        <div className="rs-topbar-inner">
          <button className="rs-wordmark" onClick={() => onNavigate('incidents')} aria-label="RecallScope home">RecallScope</button>
          <nav className="rs-primary-nav" aria-label="Primary navigation">
            <button className="rs-nav-button" data-active={view === 'incidents'} onClick={() => onNavigate('incidents')}><RadioTower size={16} />Incidents</button>
            <button className="rs-nav-button" data-active={view === 'command'} disabled={!incidentLabel} onClick={() => navigateTo('command')}><Activity size={16} />Command centre</button>
            <button className="rs-nav-button" disabled={!incidentLabel} onClick={() => navigateTo('graph')}><GitBranch size={16} />Exposure</button>
            <button className="rs-nav-button" disabled={!incidentLabel} onClick={() => navigateTo('verification')}><ListChecks size={16} />Verification</button>
          </nav>
          <div className="rs-topbar-status" aria-label="Simulation environment online"><i /><span>Simulation online</span></div>
        </div>
      </header>
      <div className="rs-context"><div className="rs-context-inner"><strong>{incidentLabel ?? 'No incident selected'}</strong><span>Evidence defines scope. Policy defines authority.</span></div></div>
      <main className="rs-main" id="main-content"><div className="rs-workspace">{children}</div></main>
      <footer className="rs-trust-footer"><div><strong><ShieldCheck size={17} /> Every action logged. Every decision traceable.</strong><p>Public notices, disposal, and release require human authorization.</p></div></footer>
    </div>
  )
}
