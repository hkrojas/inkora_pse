import { useState } from 'react';

export default function SectionNavigation({ label = 'Secciones del formulario', items = [] }) {
  const [activeId, setActiveId] = useState(items[0]?.id || '');

  const goToSection = (id) => {
    const section = document.getElementById(id);
    if (!section) return;
    setActiveId(id);
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    section.focus({ preventScroll: true });
  };

  if (!items.length) return null;

  return (
    <nav className="section-navigation" aria-label={label}>
      <span className="section-navigation__label">{label}</span>
      <div className="section-navigation__items">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`section-navigation__item${activeId === item.id ? ' is-active' : ''}`}
            aria-current={activeId === item.id ? 'step' : undefined}
            onClick={() => goToSection(item.id)}
          >
            <span>{item.label}</span>
            {item.status && <small>{item.status}</small>}
          </button>
        ))}
      </div>
    </nav>
  );
}
