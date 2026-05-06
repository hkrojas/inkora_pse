import { SkeletonTable } from './Skeleton';

export function DataTable({
  columns,
  data,
  keyExtractor,
  rowActions,
  loading = false,
  emptyState,
  onRowClick,
  className = '',
  tableClassName = '',
  rowClassName,
  selectedRowKey,
}) {
  if (loading) {
    return (
      <div className={`ink-table-card ${className}`.trim()}>
        <SkeletonTable rows={6} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    if (emptyState) return <div className={className}>{emptyState}</div>;
    return null;
  }

  return (
    <div className={`ink-table-card ${className}`.trim()}>
      <div className="ink-table-scroll">
        <table className={`ink-table ${tableClassName}`.trim()}>
          <colgroup>
            {columns.map((col) => (
              <col
                key={col.key}
                style={{
                  width: col.width,
                  minWidth: col.minWidth,
                }}
              />
            ))}
            {rowActions && <col style={{ width: 80 }} />}
          </colgroup>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={col.headerClassName || ''}
                  style={{
                    width: col.width,
                    textAlign: col.align || 'left',
                    minWidth: col.minWidth,
                  }}
                >
                  <span className="flex items-center gap-1.5">
                    {col.icon && (
                      <col.icon className="h-3 w-3 opacity-60" />
                    )}
                    {col.header}
                  </span>
                </th>
              ))}
              {rowActions && <th style={{ width: 80 }} />}
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => {
              const key = keyExtractor ? keyExtractor(item, index) : item.id ?? index;
              const isSelected = selectedRowKey !== undefined && selectedRowKey === key;
              const customRowClass = rowClassName ? rowClassName(item, index) : '';

              return (
                <tr
                  key={key}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                  className={[
                    onRowClick ? 'cursor-pointer' : '',
                    isSelected ? 'ink-table-row--active' : '',
                    customRowClass,
                  ].join(' ').trim()}
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      data-label={col.header}
                      className={col.cellClassName || ''}
                      style={{
                        textAlign: col.align || 'left',
                        width: col.width,
                        minWidth: col.minWidth,
                      }}
                    >
                      {col.render
                        ? col.render(item, index)
                        : item[col.key] ?? '--'}
                    </td>
                  ))}
                  {rowActions && (
                    <td data-label="Acciones">
                      <div className="ink-table-row-actions">
                        {rowActions(item)}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
