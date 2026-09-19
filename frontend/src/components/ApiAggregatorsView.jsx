import { useEffect, useState } from 'react'
import Card from './Card.jsx'
import { fetchProviders } from '../lib/api.js'
import { fmt, truncateText } from '../lib/scoring.js'

export default function ApiAggregatorsView() {
  const [providers, setProviders] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchProviders()
      .then(setProviders)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>API aggregators</h2>
      <p className="muted" style={{ fontSize: 14, maxWidth: 600, marginBottom: 20 }}>
        Unified-API alternatives to fal.ai, our current provider. Dado real, coletado via busca automática — nem todo campo (ex: overhead exato, latência) é publicamente divulgado por todos os provedores.
      </p>

      {error && <p className="status-msg">Não consegui buscar provedores: {error}</p>}
      {!error && !providers.length && <p className="status-msg">Carregando...</p>}

      {providers.length > 0 && (
        <Card style={{ padding: 6, overflowX: 'auto' }}>
          <table style={{ minWidth: 640 }}>
            <thead>
              <tr>
                <th>Provider</th><th className="num">Uptime</th><th>Pricing</th><th>Stability</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 600 }}>{p.name}</td>
                  <td className="num">{fmt(p.uptimePct, (v) => `${v.toFixed(2)}%`)}</td>
                  <td className="muted" style={{ fontSize: 13, maxWidth: 260 }} title={p.pricingNotes || ''}>{truncateText(p.pricingNotes)}</td>
                  <td className="muted" style={{ fontSize: 13, maxWidth: 260 }} title={p.stabilityNotes || ''}>{truncateText(p.stabilityNotes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  )
}
