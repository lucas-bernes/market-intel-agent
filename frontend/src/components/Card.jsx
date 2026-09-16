// Componente pequeno e reutilizável: evita repetir as 4 marcas de canto
// (".corner tl/tr/bl/br") em todo card do design, em todas as telas.
export default function Card({ children, style }) {
  return (
    <div className="card" style={style}>
      <i className="corner tl"></i>
      <i className="corner tr"></i>
      <i className="corner bl"></i>
      <i className="corner br"></i>
      {children}
    </div>
  )
}
