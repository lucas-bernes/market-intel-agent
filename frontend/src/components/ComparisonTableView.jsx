import Card from './Card.jsx'
import { fmt } from '../lib/scoring.js'

function MultiShotTag({ yes }) {
  return yes ? (
    <span className="chip" style={{ background: 'rgba(63,124,44,.16)', color: '#3f7c2c' }}>Yes</span>
  ) : (
    <span className="chip" style={{ background: 'rgba(58,46,33,.16)', color: '#7a6a55' }}>No</span>
  )
}

export default function ComparisonTableView({ ranked, onSelectModel }) {
  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>Comparison table</h2>
      <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>
        All models side-by-side, ranked order.
      </p>
      <Card style={{ padding: 6, overflowX: 'auto' }}>
        <table style={{ minWidth: 760 }}>
          <thead>
            <tr>
              <th>Model</th><th>Provider</th><th className="num">$/s</th><th className="num">$/image</th>
              <th className="num">Ref imgs</th><th className="num">Prompt window</th><th>Multi-shot</th>
              <th className="num">Quality</th><th className="num">Latency</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((m) => (
              <tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => onSelectModel(m.id)}>
                <td style={{ fontWeight: 600 }}>{m.name}</td>
                <td className="muted">{m.provider}</td>
                <td className="num">{fmt(m.pricePerSecond, (v) => `$${v.toFixed(3)}`)}</td>
                <td className="num">{fmt(m.pricePerImage, (v) => `$${v.toFixed(3)}`)}</td>
                <td className="num">{fmt(m.maxReferenceImages, (v) => v)}</td>
                <td className="num">{fmt(m.promptWindowTokens, (v) => v.toLocaleString())}</td>
                <td><MultiShotTag yes={m.multiShot} /></td>
                <td className="num">{fmt(m.qualityScore, (v) => `${v.toFixed(1)}/10`)}</td>
                <td className="num">{fmt(m.latencySeconds, (v) => `${v}s`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  )
}
