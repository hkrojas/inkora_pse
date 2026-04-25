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
        <div className="product-combobox-preview">
          <span className="product-combobox-code">
            {getProductCode(option.product)}
          </span>
          <span className="product-combobox-name">
            {option.product?.nombre || 'Producto'}
          </span>
        </div>
      )}
      renderOption={(option, { isActive }) => (
        <div className={`product-combobox-option ${isActive ? 'is-active' : ''}`}>
          <span className="product-combobox-code">
            {getProductCode(option.product)}
          </span>
          <span className="product-combobox-name">
            {option.product?.nombre}
          </span>
        </div>
      )}
    />
  );
}
