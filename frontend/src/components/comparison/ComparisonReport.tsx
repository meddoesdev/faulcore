import {
  ArrowRight,
  BarChart3,
  Download,
  FileText,
  Printer,
  Scale,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Run, RunMode, Scenario } from '../../types'

interface ComparisonReportProps {
  scenario: Scenario
  runs: Partial<Record<RunMode, Run>>
  onSelectMode: (mode: RunMode) => void
}

const percent = (value: number) => Math.round(value * 100)

function escapeHtml(value: string | number) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function metricRows(faultcore: Run, baseline: Run) {
  const left = faultcore.metrics!
  const right = baseline.metrics!
  return [
    { metric: 'Precision', faultcore: percent(left.containment_precision), baseline: percent(right.containment_precision) },
    { metric: 'Recall', faultcore: percent(left.containment_recall), baseline: percent(right.containment_recall) },
    { metric: 'Safe preserved', faultcore: percent(left.safe_inventory_preserved), baseline: percent(right.safe_inventory_preserved) },
    { metric: 'Under-containment', faultcore: percent(left.under_containment_rate), baseline: percent(right.under_containment_rate) },
    { metric: 'Over-containment', faultcore: percent(left.over_containment_rate), baseline: percent(right.over_containment_rate) },
  ]
}

function actionSummary(run: Run) {
  return run.actions.length
    ? run.actions.map((action) => `${action.type.replaceAll('_', ' ')} — ${action.status}`).join(', ')
    : 'No action returned'
}

function buildReport(scenario: Scenario, faultcore: Run, baseline: Run) {
  const rows = metricRows(faultcore, baseline)
    .map(({ metric, faultcore: left, baseline: right }) => `<tr><th>${escapeHtml(metric)}</th><td>${left}%</td><td>${right}%</td></tr>`)
    .join('')
  const generatedAt = new Date().toLocaleString()
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>arivu.ai incident report — ${escapeHtml(scenario.id)}</title>
<style>body{font:15px/1.5 system-ui,sans-serif;color:#14202b;max-width:920px;margin:40px auto;padding:0 24px}h1{margin-bottom:4px}small{color:#64748b}section{margin-top:30px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border:1px solid #cbd5e1;text-align:left}thead{background:#e8f7f2}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{padding:18px;border:1px solid #cbd5e1;border-radius:8px}.label{text-transform:uppercase;letter-spacing:.08em;font-size:11px;color:#64748b}@media print{body{margin:0}.no-print{display:none}}</style></head>
<body><p class="label">arivu.ai / Incident report</p><h1>${escapeHtml(scenario.name)}</h1><small>${escapeHtml(scenario.id)} · generated ${escapeHtml(generatedAt)}</small>
<section><h2>Incident</h2><p><strong>${escapeHtml(scenario.alert_type)}</strong> — ${escapeHtml(scenario.description)}</p><p>Product: ${escapeHtml(scenario.product)}</p></section>
<section><h2>Baseline versus arivu.ai</h2><table><thead><tr><th>Metric</th><th>arivu.ai</th><th>Baseline</th></tr></thead><tbody>${rows}</tbody></table></section>
<section class="grid"><div class="card"><p class="label">arivu.ai decision</p><h3>${escapeHtml(faultcore.arbiter?.decision ?? 'Not applicable')}</h3><p>${escapeHtml(faultcore.arbiter?.summary ?? faultcore.investigator?.summary ?? 'No summary')}</p><p><strong>Actions:</strong> ${escapeHtml(actionSummary(faultcore))}</p><p><strong>Residual risk:</strong> ${escapeHtml(faultcore.verification?.residual_risk ?? 'unknown')}</p></div>
<div class="card"><p class="label">Baseline result</p><h3>${escapeHtml(baseline.investigator?.summary ?? 'No summary')}</h3><p><strong>Actions:</strong> ${escapeHtml(actionSummary(baseline))}</p><p><strong>Residual risk:</strong> ${escapeHtml(baseline.verification?.residual_risk ?? 'unknown')}</p></div></section>
<section><h2>Audit identity</h2><p>arivu.ai run: ${escapeHtml(faultcore.run_id)}<br>Baseline run: ${escapeHtml(baseline.run_id)}</p></section></body></html>`
}

export function ComparisonReport({ scenario, runs, onSelectMode }: ComparisonReportProps) {
  const faultcore = runs.faultcore
  const baseline = runs.baseline
  const ready = Boolean(faultcore?.metrics && baseline?.metrics)
  const reportHref = ready && faultcore && baseline
    ? `data:text/html;charset=utf-8,${encodeURIComponent(buildReport(scenario, faultcore, baseline))}`
    : undefined

  return (
    <section className="comparison-report" aria-labelledby="comparison-heading">
      <header className="comparison-heading">
        <div>
          <p className="section-kicker"><Scale size={14} /> Decision comparison</p>
          <h2 id="comparison-heading">Baseline versus arivu.ai</h2>
          <p>Run both modes against the same reset scenario to compare containment quality.</p>
        </div>
        {ready && <div className="report-actions"><a className="secondary-button" href={reportHref} download={`arivu-ai-${scenario.id}-report.html`}><Download size={14} /> Download HTML</a><button className="secondary-button" onClick={() => window.print()}><Printer size={14} /> Print report</button></div>}
      </header>

      {!ready && (
        <div className="comparison-prompt">
          <BarChart3 size={24} />
          <div><strong>Comparison needs two completed runs</strong><p>{faultcore ? 'arivu.ai is captured. Run the baseline against the same scenario.' : baseline ? 'Baseline is captured. Run arivu.ai against the same scenario.' : 'Complete arivu.ai and baseline runs to unlock the comparison.'}</p></div>
          <button className="primary-button" onClick={() => onSelectMode(faultcore ? 'baseline' : 'faultcore')}>{faultcore ? 'Select baseline' : 'Select arivu.ai'} <ArrowRight size={14} /></button>
        </div>
      )}

      {ready && faultcore && baseline && (
        <>
          <div className="comparison-chart" role="img" aria-label="Grouped bar chart comparing arivu.ai and baseline containment metrics">
            <ResponsiveContainer width="100%" height={330}>
              <BarChart data={metricRows(faultcore, baseline)} margin={{ top: 24, right: 24, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="#e6dfd5" vertical={false} />
                <XAxis dataKey="metric" stroke="#91877d" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} unit="%" stroke="#91877d" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#fffdf9', border: '1px solid #d2c7ba', borderRadius: 12, color: '#14110f' }} formatter={(value) => [`${value}%`]} />
                <Legend />
                <Bar dataKey="faultcore" name="arivu.ai" fill="#f26a21" radius={[4, 4, 0, 0]} />
                <Bar dataKey="baseline" name="Baseline" fill="#7651a8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="comparison-table" role="table" aria-label="Metric comparison table">
            <div role="row"><strong role="columnheader">Metric</strong><strong role="columnheader">arivu.ai</strong><strong role="columnheader">Baseline</strong></div>
            {metricRows(faultcore, baseline).map((row) => <div role="row" key={row.metric}><span role="cell">{row.metric}</span><b role="cell">{row.faultcore}%</b><b role="cell">{row.baseline}%</b></div>)}
            <div role="row"><span role="cell">Time to containment</span><b role="cell">{faultcore.metrics!.time_to_containment_seconds.toFixed(2)}s</b><b role="cell">{baseline.metrics!.time_to_containment_seconds.toFixed(2)}s</b></div>
          </div>

          <article className="incident-report" id="incident-report">
            <header><div><FileText size={18} /><span>Incident report</span></div><strong>{scenario.id}</strong></header>
            <div className="report-summary"><div><span>arivu.ai decision</span><strong>{faultcore.arbiter?.decision ?? 'N/A'}</strong><p>{faultcore.arbiter?.summary ?? faultcore.investigator?.summary}</p></div><div><span>Baseline outcome</span><strong>{baseline.actions[0]?.status ?? 'No action'}</strong><p>{baseline.investigator?.summary}</p></div></div>
            <footer><span>arivu.ai run {faultcore.run_id}</span><span>Baseline run {baseline.run_id}</span></footer>
          </article>
        </>
      )}
    </section>
  )
}
