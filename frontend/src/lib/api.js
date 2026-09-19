// Vite expõe variáveis de ambiente prefixadas com VITE_ via import.meta.env.
// Em dev local sem essa variável definida, cai no valor padrão (localhost:8000).
// Em produção/Docker, isso vira configurável sem precisar mudar o código.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// A API devolve snake_case (padrão Python); o resto do app usa camelCase
// (padrão JS) — essas funções são a única "tradução" entre os dois formatos.
function fromApiModel(record) {
  return {
    id: record.model_key,
    name: record.model_name,
    provider: record.provider,
    pricePerSecond: record.price_per_second_usd,
    maxReferenceImages: record.max_reference_images,
    promptMaxChars: record.prompt_max_chars,
    multiShot: record.multi_shot_support,
    qualityScore: record.quality_score,
    docUrl: null,
    notes: record.quality_notes || record.notes || 'Sem notas ainda.',
    evidence: record.evidence || {},
  };
}

function fromApiProvider(record) {
  return {
    id: record.provider_key,
    name: record.provider_name,
    uptimePct: record.uptime_pct,
    pricingSummary: record.pricing_summary,
    stabilitySummary: record.stability_summary,
    pricingNotes: record.pricing_notes,
    stabilityNotes: record.stability_notes,
    notes: record.notes,
    evidence: record.evidence || {},
  };
}

export async function fetchModels() {
  const response = await fetch(`${API_BASE_URL}/api/models`);
  if (!response.ok) {
    throw new Error(`API respondeu status ${response.status}`);
  }
  const data = await response.json();
  return data.map(fromApiModel);
}

export async function fetchProviders() {
  const response = await fetch(`${API_BASE_URL}/api/providers`);
  if (!response.ok) {
    throw new Error(`API respondeu status ${response.status}`);
  }
  const data = await response.json();
  return data.map(fromApiProvider);
}
