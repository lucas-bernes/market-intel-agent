// Calcula o score de cada modelo com base nos pesos atuais. Campos ausentes
// (null) contribuem 0 pro score nessa dimensão, em vez de quebrar o cálculo.
export function computeScores(models, weights) {
  const prices = models.map((m) => m.pricePerSecond).filter((v) => v != null);
  const prompts = models.map((m) => m.promptWindowTokens).filter((v) => v != null);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const minPrompt = prompts.length ? Math.min(...prompts) : 0;
  const maxPrompt = prompts.length ? Math.max(...prompts) : 0;
  const totalW = weights.cost + weights.promptWindow + weights.multiShot + weights.quality || 1;

  return models
    .map((m) => {
      const costNorm =
        m.pricePerSecond == null || maxPrice === minPrice
          ? 0
          : (maxPrice - m.pricePerSecond) / (maxPrice - minPrice);
      const promptNorm =
        m.promptWindowTokens == null || maxPrompt === minPrompt
          ? 0
          : (m.promptWindowTokens - minPrompt) / (maxPrompt - minPrompt);
      const multiNorm = m.multiShot ? 1 : 0;
      const qualityNorm = m.qualityScore == null ? 0 : m.qualityScore / 10;

      const score =
        ((costNorm * weights.cost +
          promptNorm * weights.promptWindow +
          multiNorm * weights.multiShot +
          qualityNorm * weights.quality) /
          totalW) *
        100;

      return { ...m, score };
    })
    .sort((a, b) => b.score - a.score);
}

export function fmt(value, formatter) {
  return value === null || value === undefined ? '—' : formatter(value);
}

// Corta texto longo (parágrafos extraídos de review/pricing) pra não
// esticar a linha de uma tabela até virar um bloco de texto gigante.
export function truncateText(text, maxLength = 160) {
  if (!text) return '—';
  return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}…`;
}
