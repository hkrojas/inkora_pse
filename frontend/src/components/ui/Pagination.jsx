import { ChevronLeft, ChevronRight } from 'lucide-react';

function getVisiblePages(currentPage, totalPages) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = Array.from(new Set([
    1,
    currentPage - 1,
    currentPage,
    currentPage + 1,
    totalPages,
  ].filter((page) => page >= 1 && page <= totalPages))).sort((a, b) => a - b);

  return pages.reduce((items, page, index) => {
    const previous = pages[index - 1];
    if (previous && page - previous === 2) items.push(previous + 1);
    if (previous && page - previous > 2) items.push(`ellipsis-${previous}`);
    items.push(page);
    return items;
  }, []);
}

export default function Pagination({
  page,
  totalPages,
  onPageChange,
  ariaLabel = 'Paginación',
}) {
  const safeTotal = Math.max(1, Number(totalPages) || 1);
  const safePage = Math.min(Math.max(1, Number(page) || 1), safeTotal);
  const pages = getVisiblePages(safePage, safeTotal);

  const goToPage = (nextPage) => {
    const target = Math.min(Math.max(1, Number(nextPage) || 1), safeTotal);
    if (target !== safePage) onPageChange(target);
  };

  return (
    <div className="pagination" role="navigation" aria-label={ariaLabel}>
      <button
        type="button"
        className="page-btn page-btn--nav"
        disabled={safePage <= 1}
        onClick={() => goToPage(safePage - 1)}
        aria-label="Página anterior"
      >
        <ChevronLeft aria-hidden="true" size={17} strokeWidth={2.4} />
      </button>

      <div
        className={`page-numbers ${safeTotal > 5 ? 'page-numbers--condensed' : ''}`.trim()}
        aria-label={`Página ${safePage} de ${safeTotal}`}
      >
        {pages.map((item) => (
          typeof item === 'number' ? (
            <button
              key={item}
              type="button"
              className={`page-btn page-btn--number ${item === safePage ? 'active' : ''}`.trim()}
              onClick={() => goToPage(item)}
              aria-label={`Ir a página ${item}`}
              aria-current={item === safePage ? 'page' : undefined}
              data-page-edge={item === 1 || item === safeTotal ? 'true' : undefined}
            >
              {item}
            </button>
          ) : (
            <span key={item} className="page-ellipsis" aria-hidden="true">…</span>
          )
        ))}
      </div>

      <button
        type="button"
        className="page-btn page-btn--nav"
        disabled={safePage >= safeTotal}
        onClick={() => goToPage(safePage + 1)}
        aria-label="Página siguiente"
      >
        <ChevronRight aria-hidden="true" size={17} strokeWidth={2.4} />
      </button>
    </div>
  );
}
