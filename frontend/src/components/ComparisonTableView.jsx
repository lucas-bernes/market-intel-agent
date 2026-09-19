import Card from './Card.jsx'
import { fmt } from '../lib/scoring.js'

function MultiShotTag({ yes }) {
  // null = a fonte não diz; mostrar "No" afirmaria algo que não sabemos.
  if (yes == null) return <span className="muted">—</span>
  return yes ? (
    <span className="chip" style={{ background: 'rgba(74,222,128,.15)', color: '#4ade80' }}>Yes</span>
  ) : (
    <span className="chip" style={{ background: 'rgba(180,255,200,.1)', color: '#79857f' }}>No</span>
  )
}

// "*" ao lado de um valor = ainda sem citação verificada da fonte.
function mark(m, field, text) {
  return text === '—' || m.evidence[field] ? text : <>{text}<span className="muted" title="Sem citação verificada da fonte"> *</span></>
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
              <th>Model</th><th>Provider</th><th className="num">$/s</th>
              <th className="num">Ref imgs</th><th className="num">Prompt limit</th><th>Multi-shot</th>
              <th className="num">Quality</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((m) => (
              <tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => onSelectModel(m.id)}>
                <td style={{ fontWeight: 600 }}>{m.name}</td>
                <td className="muted">{m.provider}</td>
                <td className="num">{mark(m, 'price_per_second_usd', fmt(m.pricePerSecond, (v) => `$${v.toFixed(3)}`))}</td>
                <td className="num">{mark(m, 'max_reference_images', fmt(m.maxReferenceImages, (v) => v))}</td>
                <td className="num">{mark(m, 'prompt_max_chars', fmt(m.promptMaxChars, (v) => v.toLocaleString()))}</td>
                <td><MultiShotTag yes={m.multiShot} /></td>
                <td className="num">{mark(m, 'quality_score', fmt(m.qualityScore, (v) => `${v.toFixed(1)}/10`))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
        "—" = a plataforma não publica esse dado (ex.: limite de prompt do Kling e Seedance) ou ainda não há fonte confiável. Não estimamos valores. * = valor ainda sem citação verificada da fonte (clique no modelo para ver a fonte dos verificados).
      </p>
    </section>
  )
}
