const NAV_ITEMS = [
  {
    view: 'overview',
    label: 'Ranking',
    icon: <><circle cx="9" cy="9" r="6" /><circle cx="9" cy="9" r="2" /></>,
  },
  {
    view: 'table',
    label: 'Comparison table',
    icon: <><rect x="2" y="3" width="14" height="12" rx="1" /><line x1="2" y1="8" x2="16" y2="8" /><line x1="9" y1="3" x2="9" y2="15" /></>,
  },
  {
    view: 'detail',
    label: 'Model detail',
    icon: <><rect x="3" y="2" width="12" height="14" rx="1" /><line x1="6" y1="6" x2="13" y2="6" /><line x1="6" y1="9" x2="13" y2="9" /><line x1="6" y1="12" x2="11" y2="12" /></>,
  },
  {
    view: 'history',
    label: 'Price history',
    icon: <><polyline points="2,14 7,9 10,11 16,4" /><line x1="2" y1="16" x2="16" y2="16" /></>,
  },
  {
    view: 'aggregators',
    label: 'API aggregators',
    icon: <><rect x="3" y="2" width="12" height="3" /><rect x="3" y="7.5" width="12" height="3" /><rect x="3" y="13" width="12" height="3" /></>,
  },
  {
    view: 'config',
    label: 'Ranking weights',
    icon: <><line x1="2" y1="5" x2="16" y2="5" /><circle cx="11" cy="5" r="2" /><line x1="2" y1="9" x2="16" y2="9" /><circle cx="6" cy="9" r="2" /><line x1="2" y1="13" x2="16" y2="13" /><circle cx="13" cy="13" r="2" /></>,
  },
]

export default function Sidebar({ activeView, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="kicker">Views</div>
      {NAV_ITEMS.map((item) => (
        <button
          key={item.view}
          className={`navbtn${activeView === item.view ? ' active' : ''}`}
          onClick={() => onNavigate(item.view)}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
            {item.icon}
          </svg>
          <span className="navlabel">{item.label}</span>
        </button>
      ))}
    </aside>
  )
}
