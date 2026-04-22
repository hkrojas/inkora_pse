import DocumentList from '../components/documents/DocumentList';

export default function BoletasPage() {
  return (
    <DocumentList
      tipo="03"
      title="Boletas de venta"
      subtitle="Comprobantes tipo 03 emitidos ante SUNAT"
      newLabel="+ Nueva boleta"
      newHref="/comprobantes/nuevo?tipo=03"
    />
  );
}
