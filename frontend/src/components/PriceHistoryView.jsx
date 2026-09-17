import { useState } from 'react'
import Card from './Card.jsx'

// Desacoplado de verdade dos modelos reais: não guardamos histórico de
// preço ainda (só o valor atual), então essa tela continua 100%
// ilustrativa até existir esse dado.
const HISTORY_MODELS = [
  { id: 'illustrative-a', name: '(exemplo) Modelo A', history: [0.52, 0.48, 0.44, 0.40, 0.37, 0.35] },
  { id: 'illustrative-b', name: '(exemplo) Modelo B', history: [0.60, 0.58, 0.55, 0.53, 0.51, 0.50] },
  { id: 'illustrative-c', name: '(exemplo) Modelo C', history: [0.26, 0.24, 0.23, 0.22, 0.21, 0.20] },
]

const MONTHS = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']

function buildSparklinePoints(history, width, height, pad) {
  const min = Math.min(...history)
  const max = Math.max(...history)
  const range = max - min || 1
  const stepX = (width - pad * 2) / (history.length - 1)
  return history
    .map((v, i) => {
      const x = pad + i * stepX
      const y = pad + (1 - (v - min) / range) * (height - pad * 2)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

export default function PriceHistoryView() {
  const [modelId, setModelId] = useState(HISTORY_MODELS[0].id)
  const model = HISTORY_MODELS.find((m) => m.id === modelId)
  const points = buildSparklinePoints(model.history, 640, 220, 34)
  const minH = Math.min(...model.history)
  const maxH = Math.max(...model.history)

  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>Price history</h2>
      <p className="muted" style={{ fontSize: 14, marginBottom: 8 }}>
        Six-month $/second trend, per model.
      </p>
      <p className="muted" style={{ fontSize: 12, marginBottom: 20 }}>
        <span className="pill">Preview data</span> não coletamos histórico de preço real ainda — isso aqui é ilustrativo.
      </p>

      <div style={{ maxWidth: 280, marginBottom: 20 }}>
        <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>Model</label>
        <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
          {HISTORY_MODELS.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>

      <Card style={{ padding: 24, marginBottom: 20 }}>
        <svg width="100%" height="220" viewBox="0 0 640 220">
          <line x1="34" y1="190" x2="606" y2="190" stroke="rgba(58,46,33,.18)" strokeWidth="1" />
          <polyline points={points} fill="none" stroke="#6b7c2d" strokeWidth="2" />
          <text x="4" y="40" fontSize="11" fill="#8a7660">${maxH.toFixed(3)}</text>
          <text x="4" y="185" fontSize="11" fill="#8a7660">${minH.toFixed(3)}</text>
          {MONTHS.map((label, i) => {
            const x = (34 + i * ((640 - 68) / (MONTHS.length - 1))).toFixed(1)
            return <text key={label} x={x} y="208" fontSize="11" fill="#8a7660">{label}</text>
          })}
        </svg>
      </Card>

      <Card style={{ padding: 6, overflowX: 'auto' }}>
        <table style={{ maxWidth: 460 }}>
          <thead><tr><th>Month</th><th className="num">$/second</th><th className="num">Change</th></tr></thead>
          <tbody>
            {MONTHS.map((label, i) => {
              const price = model.history[i]
              const prev = i > 0 ? model.history[i - 1] : null
              const change = prev != null ? (((price - prev) / prev) * 100).toFixed(1) : null
              const isDown = change != null && Number(change) <= 0
              const color = change == null ? '#8a7660' : isDown ? '#3f7c2c' : '#a1341a'
              return (
                <tr key={label}>
                  <td>{label}</td>
                  <td className="num">${price.toFixed(3)}</td>
                  <td className="num" style={{ color }}>{change != null ? `${change > 0 ? '+' : ''}${change}%` : '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>
    </section>
  )
}
