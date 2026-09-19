import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import RankingView from './components/RankingView.jsx'
import ComparisonTableView from './components/ComparisonTableView.jsx'
import ModelDetailView from './components/ModelDetailView.jsx'
import PriceHistoryView from './components/PriceHistoryView.jsx'
import ApiAggregatorsView from './components/ApiAggregatorsView.jsx'
import RankingWeightsView, { DEFAULT_WEIGHTS } from './components/RankingWeightsView.jsx'
import { fetchModels, getSnapshot } from './lib/api.js'
import { computeScores } from './lib/scoring.js'

export default function App() {
  const [models, setModels] = useState([])
  const [loadError, setLoadError] = useState(null)
  const [view, setView] = useState('overview')
  const [selectedModelId, setSelectedModelId] = useState(null)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)

  // useEffect com [] no final: roda só uma vez, quando o componente monta
  // (equivalente ao loadModels() que chamávamos direto no fim do script,
  // na versão HTML/JS puro).
  useEffect(() => {
    fetchModels()
      .then((data) => {
        setModels(data)
        if (data.length) setSelectedModelId(data[0].id)
      })
      .catch((err) => setLoadError(err.message))
  }, [])

  const ranked = computeScores(models, weights)

  function selectModel(id) {
    setSelectedModelId(id)
    setView('detail')
  }

  return (
    <div className="app-shell">
      <div className="topnav">
        <div className="brand">Market Intelligence Agent</div>
        <span className="pill">
          {loadError
            ? 'Erro ao carregar API'
            : models.length
              ? `${models.length} modelos (dado real)${getSnapshot() ? ` · snapshot de ${new Date(getSnapshot().generated_at).toLocaleDateString()}` : ''}`
              : 'Loading...'}
        </span>
        <button className="btn btn-primary" style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>Export ↗</button>
      </div>

      <Sidebar activeView={view} onNavigate={setView} />

      <main>
        {loadError && (
          <p className="status-msg">
            Não consegui buscar dados da API: {loadError}. Ela está rodando?
            (<code>python -m uvicorn market_intel.api:app --reload</code>)
          </p>
        )}

        {!loadError && !models.length && <p className="status-msg">Carregando dados da API...</p>}

        {!loadError && models.length > 0 && (
          <>
            {view === 'overview' && (
              <RankingView ranked={ranked} onSelectModel={selectModel} onAdjustWeights={() => setView('config')} />
            )}
            {view === 'table' && <ComparisonTableView ranked={ranked} onSelectModel={selectModel} />}
            {view === 'detail' && (
              <ModelDetailView ranked={ranked} selectedModelId={selectedModelId} onBack={() => setView('overview')} />
            )}
            {view === 'history' && <PriceHistoryView />}
            {view === 'aggregators' && <ApiAggregatorsView />}
            {view === 'config' && <RankingWeightsView weights={weights} onChangeWeights={setWeights} />}
          </>
        )}
      </main>
    </div>
  )
}
