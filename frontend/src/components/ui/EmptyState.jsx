import { Inbox } from 'lucide-react';

export default function EmptyState({ title = 'Sin resultados', description, action }) {
  return (
    <div className="ink-empty">
      <div className="ink-empty-icon">
        <Inbox className="h-6 w-6" />
      </div>
      <h3 className="ink-empty-title">{title}</h3>
      {description && <p className="ink-empty-desc">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
