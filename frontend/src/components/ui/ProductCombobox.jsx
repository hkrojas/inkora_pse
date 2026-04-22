import CustomSelect from './CustomSelect';

function getProductCode(product) {
  return product?.codigo_interno?.trim() || 'Sin codigo';
}

function getProductPreview(product) {
  return `${getProductCode(product)} - ${product?.nombre || ''}`;
}

export default function ProductCombobox({
  products = [],
  value,
  onChange,
  onUseFreeText,
}) {
  const options = products.map((product) => ({
    value: String(product.id),
    label: getProductPreview(product),
    searchText: `${product.codigo_interno || ''} ${product.nombre || ''}`,
    product,
  }));

  return (
    <CustomSelect
      compact
      value={value}
      onChange={onChange}
      options={options}
      placeholder="Buscar por codigo o nombre..."
      searchable
      searchPlaceholder="Codigo o nombre del producto..."
      footerAction={{ label: '+ Usar descripcion libre', onClick: onUseFreeText }}
      renderPreview={(option) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <span
            style={{
              flexShrink: 0,
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {getProductCode(option.product)}
          </span>
          <span
            style={{
              display: 'block',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: '12px',
              fontWeight: 700,
              color: '#0F172A',
            }}
          >
            {option.product?.nombre || 'Producto'}
          </span>
        </div>
      )}
      renderOption={(option, { isActive }) => (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '96px minmax(0, 1fr)',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
          }}
        >
          <span
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: isActive ? '#4338CA' : '#94A3B8',
            }}
          >
            {getProductCode(option.product)}
          </span>
          <span
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontWeight: 700,
              color: isActive ? '#4338CA' : '#0F172A',
            }}
          >
            {option.product?.nombre}
          </span>
        </div>
      )}
    />
  );
}
