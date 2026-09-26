// Selo de preço promocional. O preço de tabela (o que o ranking usa) continua
// sendo o valor principal; este selo só avisa que existe uma promoção
// temporária e qual é o preço promocional. Nunca entra no cálculo do ranking.
export default function PromoBadge({ price, quote }) {
  if (price == null) return null
  const tip = `Preço promocional (temporário), fora do ranking.${quote ? ` Fonte: "${quote}"` : ''}`
  return (
    <span
      className="chip"
      title={tip}
      style={{ background: 'rgba(251,146,60,.18)', color: '#fb923c', marginLeft: 6, whiteSpace: 'nowrap' }}
    >
      PROMO ${price.toFixed(3)}/s
    </span>
  )
}
