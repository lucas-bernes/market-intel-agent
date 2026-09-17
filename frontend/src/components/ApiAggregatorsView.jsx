import Card from './Card.jsx'

// Ilustrativo: ainda não pesquisamos provedores de API de verdade
// (a "Frente B" do projeto, pendente).
const AGGREGATORS = [
  { id: 'fal', name: 'fal.ai', current: true, overheadPct: 8, uptimePct: 99.5, modelsSupported: 6, addedLatencyMs: 120, notes: 'Current provider. Fastest to add day-one releases.' },
  { id: 'replicate', name: 'Replicate', current: false, overheadPct: 12, uptimePct: 99.7, modelsSupported: 5, addedLatencyMs: 200, notes: 'Broadest catalog, slower to onboard new video releases.' },
  { id: 'together', name: 'Together AI', current: false, overheadPct: 6, uptimePct: 99.2, modelsSupported: 3, addedLatencyMs: 90, notes: 'Lowest overhead, limited video-model coverage today.' },
  { id: 'baseten', name: 'Baseten', current: false, overheadPct: 10, uptimePct: 99.6, modelsSupported: 4, addedLatencyMs: 150, notes: 'Best fit as a self-hosted fallback.' },
]

export default function ApiAggregatorsView() {
  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>API aggregators</h2>
      <p className="muted" style={{ fontSize: 14, maxWidth: 600, marginBottom: 8 }}>
        Unified-API alternatives to fal.ai, our current provider.
      </p>
      <p className="muted" style={{ fontSize: 12, marginBottom: 20 }}>
        <span className="pill">Preview data</span> ainda não pesquisamos provedores de verdade — isso aqui é ilustrativo.
      </p>
      <Card style={{ padding: 6, overflowX: 'auto' }}>
        <table style={{ minWidth: 640 }}>
          <thead>
            <tr>
              <th>Aggregator</th><th></th><th className="num">Overhead</th><th className="num">Uptime</th>
              <th className="num">Coverage</th><th className="num">Added latency</th><th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {AGGREGATORS.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{a.name}</td>
                <td>
                  {a.current ? (
                    <span className="chip" style={{ background: 'rgba(180,83,9,.15)', color: '#8a3f0a' }}>Current</span>
                  ) : (
                    <span className="chip" style={{ border: '1px solid rgba(58,46,33,.22)', color: '#7a6a55' }}>Alternative</span>
                  )}
                </td>
                <td className="num">{a.overheadPct}%</td>
                <td className="num">{a.uptimePct.toFixed(1)}%</td>
                <td className="num">{a.modelsSupported} / 7</td>
                <td className="num">{a.addedLatencyMs} ms</td>
                <td className="muted" style={{ fontSize: 13, maxWidth: 220 }}>{a.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  )
}
