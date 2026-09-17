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
      <button className="btn-ghost" style={{ marginBottom: 16 }} onClick={onBack}>
        ← Back to ranking
      </button>

      <Card style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: '#a3e635' }}>Rank #{rank}</div>
          <h2 style={{ fontSize: 26, fontWeight: 700, margin: '6px 0 4px' }}>{model.name}</h2>
          <div className="muted" style={{ fontSize: 14 }}>{model.provider}</div>
        </div>
        <div className="score-box">
          <div style={{ fontSize: 34, fontWeight: 700 }}>{model.score.toFixed(1)}</div>
          <div className="muted" style={{ fontSize: 12 }}>score / 100</div>
        </div>
      </Card>

      <div className="spec-grid">
        {specs.map(([label, value]) => (
          <Card key={label}>
            <div style={{ fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: '#8b9690', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>{value}</div>
          </Card>
        ))}
      </div>

      <div style={{ marginBottom: 24 }}>
        <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Notes</h4>
        <p style={{ maxWidth: 640, margin: 0, color: '#c6cec9', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{model.notes}</p>
      </div>

      {model.docUrl ? (
        <a className="btn btn-primary" style={{ display: 'inline-block', textDecoration: 'none' }} href={model.docUrl} target="_blank" rel="noreferrer">
          View provider docs ↗
        </a>
      ) : (
        <button className="btn" disabled>Provider docs not linked yet</button>
      )}
    </section>
  )
}
