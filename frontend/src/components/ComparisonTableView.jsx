import { fmt } from '../lib/scoring.js'

export default function ComparisonTableView({ ranked, onSelectModel }) {
  return (
    <section>
      <h2>Comparison table</h2>
      <p className="text-muted" style={{ fontSize: 14, marginBottom: 20, display: 'block' }}>
        All models side-by-side, ranked order.
      </p>
      <div style={{ overflowX: 'auto' }}>
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
                <td style={{ fontWeight: 500 }}>{m.name}</td>
                <td>{m.provider}</td>
                <td className="num">{fmt(m.pricePerSecond, (v) => `$${v.toFixed(3)}`)}</td>
                <td className="num">{fmt(m.pricePerImage, (v) => `$${v.toFixed(3)}`)}</td>
                <td className="num">{fmt(m.maxReferenceImages, (v) => v)}</td>
                <td className="num">{fmt(m.promptWindowTokens, (v) => v.toLocaleString())}</td>
                <td><span className={`tag ${m.multiShot ? 'tag-accent' : 'tag-neutral'}`}>{m.multiShot ? 'Yes' : 'No'}</span></td>
                <td className="num">{fmt(m.qualityScore, (v) => `${v.toFixed(1)}/10`)}</td>
                <td className="num">{fmt(m.latencySeconds, (v) => `${v}s`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
