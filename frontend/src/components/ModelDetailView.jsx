import Card from './Card.jsx'
import PromoBadge from './PromoBadge.jsx'
import { fmt } from '../lib/scoring.js'

// Mostra de onde veio o número: link pra fonte (com a frase citada no
// tooltip) ou aviso de que ainda não há prova registrada pra esse valor.
function SourceTag({ evidence }) {
  if (!evidence) {
    return <div className="muted" style={{ fontSize: 11, marginTop: 6 }} title="Valor sem citação verificada da fonte">não verificado</div>
  }
  const date = new Date(evidence.collected_at).toLocaleDateString()
  const tip = `"${evidence.quote}" — coletado em ${date}`
  return evidence.source_url ? (
    <a href={evidence.source_url} target="_blank" rel="noreferrer" title={tip} style={{ fontSize: 11, marginTop: 6, display: 'inline-block', color: '#a3e635' }}>fonte ↗ · {date}</a>
  ) : (
    <div className="muted" style={{ fontSize: 11, marginTop: 6 }} title={tip}>verificado · {date}</div>
  )
}

export default function ModelDetailView({ ranked, discontinued = [], selectedModelId, onBack }) {
  const model = ranked.find((m) => m.id === selectedModelId) || discontinued.find((m) => m.id === selectedModelId) || ranked[0]
  const isDiscontinued = model.discontinued === true
  const rank = ranked.findIndex((m) => m.id === model.id) + 1
  const discontinuedEvidence = model.evidence.discontinued

  const specs = [
    ['$ / second', fmt(model.pricePerSecond, (v) => `$${v.toFixed(4)}`), 'price_per_second_usd'],
    ['Max ref images', fmt(model.maxReferenceImages, (v) => v), 'max_reference_images'],
    ['Prompt limit', fmt(model.promptMaxChars, (v) => `${v.toLocaleString()} chars`), 'prompt_max_chars'],
    ['Multi-shot', model.multiShot == null ? '—' : model.multiShot ? 'Yes' : 'No', 'multi_shot_support'],
    ['Quality score', fmt(model.qualityScore, (v) => `${v}/10`), 'quality_score'],
  ]

  return (
    <section>
      <button className="btn-ghost" style={{ marginBottom: 16 }} onClick={onBack}>
        ← Back to ranking
      </button>

      <Card style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: isDiscontinued ? '#f87171' : '#a3e635' }}>
            {isDiscontinued ? 'Discontinued — not ranked' : `Rank #${rank}`}
          </div>
          <h2 style={{ fontSize: 26, fontWeight: 700, margin: '6px 0 4px' }}>{model.name}</h2>
          <div className="muted" style={{ fontSize: 14 }}>{model.provider}</div>
        </div>
        {!isDiscontinued && (
          <div className="score-box">
            <div style={{ fontSize: 34, fontWeight: 700 }}>{model.score.toFixed(1)}</div>
            <div className="muted" style={{ fontSize: 12 }}>score / 100</div>
          </div>
        )}
      </Card>

      {isDiscontinued && (
        <Card style={{ marginBottom: 24, borderColor: 'rgba(248,113,113,.4)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#f87171', marginBottom: 6 }}>Este modelo foi descontinuado</div>
          <p className="muted" style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>
            Fica fora do ranking; os valores abaixo são os últimos conhecidos.
            {discontinuedEvidence && (
              <>
                {' '}Fonte: "{discontinuedEvidence.quote}"{' '}
                {discontinuedEvidence.source_url && (
                  <a href={discontinuedEvidence.source_url} target="_blank" rel="noreferrer" style={{ color: '#a3e635' }}>
                    página ↗
                  </a>
                )}
                {' '}· confirmado em {new Date(discontinuedEvidence.collected_at).toLocaleDateString()}
              </>
            )}
          </p>
        </Card>
      )}

      <div className="spec-grid">
        {specs.map(([label, value, field]) => (
          <Card key={label}>
            <div style={{ fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: '#8b9690', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>{value}</div>
            {value !== '—' && <SourceTag evidence={model.evidence[field]} />}
            {field === 'price_per_second_usd' && model.promoPricePerSecond != null && (
              <div style={{ marginTop: 8 }}>
                <PromoBadge price={model.promoPricePerSecond} quote={model.evidence.promo_price_per_second_usd?.quote} />
                <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>promoção temporária, fora do ranking</div>
              </div>
            )}
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
