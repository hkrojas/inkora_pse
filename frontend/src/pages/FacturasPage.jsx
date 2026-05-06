import DocumentList from '../components/documents/DocumentList';

export default function FacturasPage() {
  return (
    <div className="facturas-page">
      <DocumentList
        tipo="01"
        title="Facturas emitidas"
        subtitle="Comprobantes tipo 01 emitidos ante SUNAT"
        newLabel="+ Nueva factura"
        newHref="/comprobantes/nuevo?tipo=01"
      />
    </div>
  );
}
