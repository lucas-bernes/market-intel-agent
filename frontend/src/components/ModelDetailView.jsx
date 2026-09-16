import Card from './Card.jsx'
import { fmt } from '../lib/scoring.js'

export default function ModelDetailView({ ranked, selectedModelId, onBack }) {
  const model = ranked.find((m) => m.id === selectedModelId) || ranked[0]
  const rank = ranked.findIndex((m) => m.id === model.id) + 1

  const specs = [
    ['$ / second', fmt(model.pricePerSecond, (v) => `$${v.toFixed(3)}`)],
    ['$ / image', fmt(model.pricePerImage, (v) => `$${v.toFixed(3)}`)],
    ['Max ref images', fmt(model.maxReferenceImages, (v) => v)],
    ['Prompt window', fmt(model.promptWindowTokens, (v) => `${v} tok`)],
    ['Multi-shot', model.multiShot ? 'Yes' : 'No'],
    ['Quality score', fmt(model.qualityScore, (v) => `${v}/10`)],
    ['Latency', fmt(model.latencySeconds, (v) => `${v}s`)],
  ]

  return (
    <section>
      <button className="btn btn-ghost" style={{ marginBottom: 16 }} onClick={onBack}>
        ← Back to ranking
      </button>

      <Card style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>Rank #{rank}</div>
          <h2 style={{ marginTop: 2 }}>{model.name}</h2>
          <div className="text-muted">{model.provider}</div>
        </div>
        <div className="score-box">
          <div className="num" style={{ fontSize: 36 }}>{model.score.toFixed(1)}</div>
          <div className="text-muted" style={{ fontSize: 12 }}>score / 100</div>
        </div>
      </Card>

      <div className="spec-grid">
        {specs.map(([label, value]) => (
          <Card key={label}>
            <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-accent)' }}>{label}</div>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 17 }}>{value}</div>
          </Card>
        ))}
      </div>

      <div style={{ marginBottom: 24 }}>
        <h4>Notes</h4>
        <p style={{ maxWidth: 640, whiteSpace: 'pre-wrap' }}>{model.notes}</p>
      </div>

      {model.docUrl ? (
        <a className="btn" href={model.docUrl} target="_blank" rel="noreferrer">View provider docs ↗</a>
      ) : (
        <button className="btn" disabled>Provider docs not linked yet</button>
      )}
    </section>
  )
}
