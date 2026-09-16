import Card from './Card.jsx'
import { fmt } from '../lib/scoring.js'

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

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 32 }}>
        <div>
          <h2>Ranking</h2>
          <p className="text-muted" style={{ fontSize: 14, maxWidth: 560 }}>
            Scored by cost per second, prompt window, multi-shot support and quality (quando disponível).
          </p>
        </div>
        <button className="btn" style={{ whiteSpace: 'nowrap' }} onClick={onAdjustWeights}>
          Adjust weights
        </button>
      </div>

      <div className="kpi-grid">
        <Card>
          <div className="tag-outline" style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>Cheapest / sec</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, marginTop: 6 }}>{cheapest ? cheapest.name : '—'}</div>
          <div className="text-muted" style={{ fontSize: 11, marginTop: 4 }}>{cheapest ? `$${cheapest.pricePerSecond.toFixed(3)}/s` : 'sem dado'}</div>
        </Card>
        <Card>
          <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>Largest prompt window</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, marginTop: 6 }}>{largestPrompt ? largestPrompt.name : '—'}</div>
          <div className="text-muted" style={{ fontSize: 11, marginTop: 4 }}>{largestPrompt ? `${largestPrompt.promptWindowTokens} tokens` : 'sem dado'}</div>
        </Card>
        <Card>
          <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>Best quality score</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, marginTop: 6 }}>{bestQuality ? bestQuality.name : '—'}</div>
          <div className="text-muted" style={{ fontSize: 11, marginTop: 4 }}>{bestQuality ? `${bestQuality.qualityScore}/10` : 'sem nota numérica ainda'}</div>
        </Card>
        <Card>
          <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>Multi-shot support</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, marginTop: 6 }}>{multiShotCount} of {ranked.length} models</div>
          <div className="text-muted" style={{ fontSize: 11, marginTop: 4 }}>Reduces reference-image need</div>
        </Card>
      </div>

      <div>
        {ranked.map((m, i) => (
          <Card key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 20, cursor: 'pointer', padding: '18px 22px', marginBottom: 10 }}>
            <div className="rank-row-click" onClick={() => onSelectModel(m.id)} style={{ display: 'contents' }}>
              <div className="rank-badge">{i + 1}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'var(--font-heading)', fontSize: 17 }}>{m.name}</span>
                  <span className="text-muted" style={{ fontSize: 12 }}>{m.provider}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                  <span className="tag tag-accent">{fmt(m.pricePerSecond, (v) => `$${v.toFixed(3)}/s`)}</span>
                  <span className="tag tag-accent">{fmt(m.promptWindowTokens, (v) => `${v.toLocaleString()} tok`)}</span>
                  <span className={`tag ${m.multiShot ? 'tag-accent' : 'tag-neutral'}`}>Multi-shot: {m.multiShot ? 'Yes' : 'No'}</span>
                </div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${m.score.toFixed(0)}%` }}></div></div>
              </div>
              <div className="score-box">
                <div className="num">{m.score.toFixed(1)}</div>
                <div className="text-muted" style={{ fontSize: 11 }}>score / 100</div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </section>
  )
}
