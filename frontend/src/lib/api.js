// Vite expõe variáveis de ambiente prefixadas com VITE_ via import.meta.env.
// Em dev local sem essa variável definida, cai no valor padrão (localhost:8000).
// Em produção/Docker, isso vira configurável sem precisar mudar o código.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_URL = `${API_BASE_URL}/api/models`;

// A API devolve snake_case (padrão Python); o resto do app usa camelCase
// (padrão JS) — essa função é a única "tradução" entre os dois formatos.
function fromApi(record) {
  return {
    id: record.model_key,
    name: record.model_name,
    provider: record.provider,
    pricePerSecond: record.price_per_second_usd,
    pricePerImage: null, // não coletamos esse dado ainda
    maxReferenceImages: record.max_reference_images,
    promptWindowTokens: record.prompt_window_tokens,
    multiShot: record.multi_shot_support,
    qualityScore: null, // temos só quality_notes (texto), não nota numérica ainda
    latencySeconds: null, // não coletamos esse dado ainda
    docUrl: null,
    notes: record.quality_notes || record.notes || 'Sem notas ainda.',
  };
}

export async function fetchModels() {
  const response = await fetch(API_URL);
  if (!response.ok) {
    throw new Error(`API respondeu status ${response.status}`);
  }
  const data = await response.json();
  return data.map(fromApi);
}
