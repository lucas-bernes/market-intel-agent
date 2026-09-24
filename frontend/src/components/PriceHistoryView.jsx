import { useEffect, useState } from 'react'
import Card from './Card.jsx'
import { fetchHistory, fetchModels } from '../lib/api.js'

const FIELD = 'price_per_second_usd'

// Agrupa as entradas de /api/history (uma linha por mudança já confirmada)
// numa série por modelo: [{ value, changedAt }], mais antiga primeiro.
function buildSeries(history, models) {
  const nameByKey = Object.fromEntries(models.map((m) => [m.id, m.name]))
  const byKey = {}
  for (const entry of history) {
    if (entry.entity_type !== 'model' || entry.field !== FIELD) continue
    byKey[entry.entity_key] ??= []
    byKey[entry.entity_key].push({ value: Number(entry.new_value), changedAt: entry.changed_at })
  }
  return Object.entries(byKey)
    .map(([key, points]) => ({ id: key, name: nameByKey[key] || key, points }))
    .filter((s) => s.points.length)
}

function buildSparklinePoints(points, width, height, pad) {
  const values = points.map((p) => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0
  return points
    .map((p, i) => {
      const x = pad + i * stepX
      const y = pad + (1 - (p.value - min) / range) * (height - pad * 2)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

export default function PriceHistoryView() {
  const [series, setSeries] = useState(null)
  const [seriesId, setSeriesId] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([fetchHistory(), fetchModels()])
      .then(([history, models]) => {
        const built = buildSeries(history, models)
        setSeries(built)
        if (built.length) setSeriesId(built[0].id)
      })
      .catch((err) => setError(err.message))
  }, [])

  const selected = series?.find((s) => s.id === seriesId)
  const multiPoint = selected && selected.points.length > 1
  const points = multiPoint ? buildSparklinePoints(selected.points, 640, 220, 34) : null
  const values = selected ? selected.points.map((p) => p.value) : []

  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>Price history</h2>
      <p className="muted" style={{ fontSize: 14, marginBottom: 8 }}>
        $/second over time, per model — built from every value change the pipeline has confirmed so far.
      </p>
      <p className="muted" style={{ fontSize: 12, marginBottom: 20 }}>
        <span className="pill">Dado real</span> a linha do tempo só existe a partir de quando cada campo passou a ser rastreado (feat: field_history); não há dados anteriores a isso.
      </p>

      {error && <p className="status-msg">Não consegui buscar histórico: {error}</p>}
      {!error && !series && <p className="status-msg">Carregando...</p>}
      {!error && series && !series.length && (
        <p className="status-msg">Nenhuma mudança de preço confirmada ainda. Volte depois de a coleta rodar mais alguma vez.</p>
      )}

      {series && series.length > 0 && (
        <>
          <div style={{ maxWidth: 280, marginBottom: 20 }}>
            <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>Model</label>
            <select value={seriesId} onChange={(e) => setSeriesId(e.target.value)}>
              {series.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {!multiPoint ? (
            <Card style={{ padding: 24, marginBottom: 20 }}>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                Só há 1 valor confirmado pra {selected.name} até agora ({values[0] != null ? `$${values[0].toFixed(4)}/s` : '—'}).
                O gráfico aparece a partir da 2ª mudança de preço detectada pela coleta.
              </p>
            </Card>
          ) : (
            <Card style={{ padding: 24, marginBottom: 20 }}>
              <svg width="100%" height="220" viewBox="0 0 640 220">
                <line x1="34" y1="190" x2="606" y2="190" stroke="rgba(180,255,200,.12)" strokeWidth="1" />
                <polyline points={points} fill="none" stroke="#eab308" strokeWidth="2" />
                <text x="4" y="40" fontSize="11" fill="#8b9690">${Math.max(...values).toFixed(4)}</text>
                <text x="4" y="185" fontSize="11" fill="#8b9690">${Math.min(...values).toFixed(4)}</text>
              </svg>
            </Card>
          )}

          <Card style={{ padding: 6, overflowX: 'auto' }}>
            <table style={{ maxWidth: 520 }}>
              <thead><tr><th>Collected</th><th className="num">$/second</th><th className="num">Change</th></tr></thead>
              <tbody>
                {selected.points.map((p, i) => {
                  const prev = i > 0 ? selected.points[i - 1].value : null
                  const change = prev != null ? (((p.value - prev) / prev) * 100).toFixed(1) : null
                  const isDown = change != null && Number(change) <= 0
                  const color = change == null ? '#8b9690' : isDown ? '#4ade80' : '#f87171'
                  return (
                    <tr key={p.changedAt}>
                      <td>{new Date(p.changedAt).toLocaleDateString()}</td>
                      <td className="num">${p.value.toFixed(4)}</td>
                      <td className="num" style={{ color }}>{change != null ? `${change > 0 ? '+' : ''}${change}%` : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </section>
  )
}
