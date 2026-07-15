/**
 * Cabecera editorial compartida para las pantallas operativas de Inkora.
 * Mantiene el contexto de cada módulo sin convertir todas las páginas en el
 * mismo flujo visual.
 */
export default function OperationalPageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
  variant = 'catalog',
  className = '',
}) {
  return (
    <header className={`operational-page-header operational-page-header--${variant} ink-enter-1 ${className}`.trim()}>
      <div className="operational-page-header__copy">
        {eyebrow && <p className="operational-page-header__eyebrow">{eyebrow}</p>}
        <h2 className="operational-page-header__title">{title}</h2>
        {description && <p className="operational-page-header__description">{description}</p>}
        {meta && <div className="operational-page-header__meta">{meta}</div>}
      </div>
      {actions && <div className="operational-page-header__actions">{actions}</div>}
    </header>
  );
}
