export default function Pagination({
  page,
  totalPages,
  onPageChange,
  ariaLabel = 'Paginacion',
}) {
  const safeTotal = Math.max(1, Number(totalPages) || 1);
  const safePage = Math.min(Math.max(1, Number(page) || 1), safeTotal);
  const pages = Array.from({ length: safeTotal }, (_, index) => index + 1);

  const goToPage = (nextPage) => {
    const target = Math.min(Math.max(1, Number(nextPage) || 1), safeTotal);
    if (target !== safePage) onPageChange(target);
  };

  return (
    <div className="pagination" role="navigation" aria-label={ariaLabel}>
      <button
        type="button"
        className="page-btn"
        disabled={safePage <= 1}
        onClick={() => goToPage(safePage - 1)}
        aria-label="Pagina anterior"
      >
        &#8249;
      </button>

      <label className="page-jump">
        <span className="sr-only">Ir a pagina</span>
        <select
          className="page-select"
          value={safePage}
          onChange={(event) => goToPage(event.target.value)}
          aria-label="Seleccionar pagina"
        >
          {pages.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      <span className="page-total">de {safeTotal}</span>

      <button
        type="button"
        className="page-btn"
        disabled={safePage >= safeTotal}
        onClick={() => goToPage(safePage + 1)}
        aria-label="Pagina siguiente"
      >
        &#8250;
      </button>
    </div>
  );
}
