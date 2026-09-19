const DEFAULT_WEIGHTS = { cost: 35, promptWindow: 20, multiShot: 15, quality: 30 }

const ROWS = [
  ['Cost per second', 'cost'],
  ['Prompt limit', 'promptWindow'],
  ['Multi-shot support', 'multiShot'],
  ['Quality score', 'quality'],
]

export default function RankingWeightsView({ weights, onChangeWeights }) {
  return (
    <section>
      <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>Ranking weights</h2>
      <p className="muted" style={{ fontSize: 14, maxWidth: 520, marginBottom: 24 }}>
        Adjust how much each factor counts toward the ranking score. Changes apply immediately.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 22, maxWidth: 480 }}>
        {ROWS.map(([label, key]) => (
          <div key={key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 6 }}>
              <span>{label}</span>
              <span className="muted">{weights[key]}</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={weights[key]}
              onChange={(e) => onChangeWeights({ ...weights, [key]: Number(e.target.value) })}
            />
          </div>
        ))}
        <button className="btn" onClick={() => onChangeWeights(DEFAULT_WEIGHTS)}>
          Reset to defaults
        </button>
        <p className="muted" style={{ fontSize: 12, margin: 0 }}>
          Weights don't need to total 100 — the score is normalized automatically.
        </p>
      </div>
    </section>
  )
}

export { DEFAULT_WEIGHTS }
