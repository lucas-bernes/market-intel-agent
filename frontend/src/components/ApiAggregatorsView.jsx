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
      <h2>API aggregators</h2>
      <p className="text-muted" style={{ fontSize: 14, maxWidth: 600, marginBottom: 8, display: 'block' }}>
        Unified-API alternatives to fal.ai, our current provider.
      </p>
      <p className="text-muted" style={{ fontSize: 12, marginBottom: 20, display: 'block' }}>
        <span className="tag tag-outline">Preview data</span> ainda não pesquisamos provedores de verdade — isso aqui é ilustrativo.
      </p>
      <div style={{ overflowX: 'auto' }}>
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
                <td style={{ fontWeight: 500 }}>{a.name}</td>
                <td><span className={`tag ${a.current ? 'tag-accent' : 'tag-outline'}`}>{a.current ? 'Current' : 'Alternative'}</span></td>
                <td className="num">{a.overheadPct}%</td>
                <td className="num">{a.uptimePct.toFixed(1)}%</td>
                <td className="num">{a.modelsSupported} / 7</td>
                <td className="num">{a.addedLatencyMs} ms</td>
                <td className="text-muted" style={{ fontSize: 13, maxWidth: 220 }}>{a.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
