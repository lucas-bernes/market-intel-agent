import { fmt } from '../lib/scoring.js'

function MultiShotChip({ yes }) {
  return yes ? (
    <span className="chip" style={{ background: 'rgba(63,124,44,.16)', color: '#3f7c2c' }}>Multi-shot: Yes</span>
  ) : (
    <span className="chip" style={{ background: 'rgba(58,46,33,.16)', color: '#7a6a55' }}>Multi-shot: No</span>
  )
}

export default function RankingView({ ranked, onSelectModel, onAdjustWeights }) {
  const withPrice = ranked.filter((m) => m.pricePerSecond != null)
  const withPrompt = ranked.filter((m) => m.promptWindowTokens != null)
  const withQuality = ranked.filter((m) => m.qualityScore != null)

  const cheapest = withPrice.length
    ? [...withPrice].sort((a, b) => a.pricePerSecond - b.pricePerSecond)[0]
    : null
  const largestPrompt = withPrompt.length
    ? [...withPrompt].sort((a, b) => b.promptWindowTokens - a.promptWindowTokens)[0]
    : null
  const bestQuality = withQuality.length
    ? [...withQuality].sort((a, b) => b.qualityScore - a.qualityScore)[0]
    : null
  const multiShotCount = ranked.filter((m) => m.multiShot).length

  const kpis = [
    {
      label: 'Cheapest / sec',
      color: ['rgba(180,83,9,.16)', '#b4560c'],
      icon: <path d="M2 12l3-4 3 2 3-5 3 3" />,
      value: cheapest ? cheapest.name : '—',
      sub: cheapest ? `$${cheapest.pricePerSecond.toFixed(3)}/s` : 'sem dado',
    },
    {
      label: 'Largest prompt window',
      color: ['rgba(180,131,17,.18)', '#a4820f'],
      icon: <><rect x="2" y="2" width="12" height="12" rx="2" /><line x1="2" y1="7" x2="14" y2="7" /></>,
      value: largestPrompt ? largestPrompt.name : '—',
      sub: largestPrompt ? `${largestPrompt.promptWindowTokens} tokens` : 'sem dado',
    },
    {
      label: 'Best quality score',
      color: ['rgba(107,124,45,.18)', '#6b7c2d'],
      icon: <><circle cx="8" cy="8" r="6" /><path d="M8 5v3l2 2" /></>,
      value: bestQuality ? bestQuality.name : '—',
      sub: bestQuality ? `${bestQuality.qualityScore}/10` : 'sem nota numérica ainda',
    },
    {
      label: 'Multi-shot support',
      color: ['rgba(161,98,7,.18)', '#a16207'],
      icon: <><rect x="2" y="9" width="3" height="5" /><rect x="6.5" y="5" width="3" height="9" /><rect x="11" y="2" width="3" height="12" /></>,
      value: `${multiShotCount} of ${ranked.length} models`,
      sub: 'Reduces reference-image need',
    },
  ]

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>Ranking</h2>
          <p className="muted" style={{ fontSize: 14, maxWidth: 560 }}>
            Scored by cost per second, prompt window, multi-shot support and quality (quando disponível).
          </p>
        </div>
        <button className="btn" style={{ whiteSpace: 'nowrap' }} onClick={onAdjustWeights}>
          Adjust weights
        </button>
      </div>

      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div className="kpi-card" key={kpi.label}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div className="kpi-icon" style={{ background: kpi.color[0], color: kpi.color[1] }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">{kpi.icon}</svg>
              </div>
              <div style={{ fontSize: 11 }} className="muted">{kpi.label}</div>
            </div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{kpi.value}</div>
            <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {ranked.map((m, i) => (
          <div className="rank-row" key={m.id} onClick={() => onSelectModel(m.id)}>
            <div className="rank-badge">{i + 1}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 16, fontWeight: 600 }}>{m.name}</span>
                <span className="muted" style={{ fontSize: 12 }}>{m.provider}</span>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                <span className="chip" style={{ background: 'rgba(180,131,17,.16)', color: '#8f6b12' }}>{fmt(m.pricePerSecond, (v) => `$${v.toFixed(3)}/s`)}</span>
                <span className="chip" style={{ background: 'rgba(107,124,45,.16)', color: '#5c6b26' }}>{fmt(m.promptWindowTokens, (v) => `${v.toLocaleString()} tok`)}</span>
                <MultiShotChip yes={m.multiShot} />
              </div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${m.score.toFixed(0)}%` }}></div></div>
            </div>
            <div className="score-box">
              <div style={{ fontSize: 22, fontWeight: 700 }}>{m.score.toFixed(1)}</div>
              <div className="muted" style={{ fontSize: 11 }}>score / 100</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
