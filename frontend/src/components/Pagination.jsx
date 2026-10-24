import { ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZES = [10, 20, 50, 100];

function pageWindow(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const result = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) result.push('…' + p);
    result.push(p);
  });
  return result;
}

export default function Pagination({ page, pages, total, pageSize, onPageChange, onPageSizeChange }) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-col gap-3 border-t border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3 text-sm text-secondary">
        <span>
          Showing <span className="font-medium text-ink">{from}</span>–<span className="font-medium text-ink">{to}</span>{' '}
          of <span className="font-medium text-ink">{total}</span>
        </span>
        <label htmlFor="page-size" className="sr-only">
          Rows per page
        </label>
        <select
          id="page-size"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="field-input w-auto py-1"
        >
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size} / page
            </option>
          ))}
        </select>
      </div>

      <nav aria-label="Pagination" className="flex items-center gap-1">
        <button
          type="button"
          className="icon-btn"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {pageWindow(page, pages).map((p) =>
          typeof p === 'string' ? (
            <span key={p} className="px-1 text-secondary" aria-hidden="true">
              …
            </span>
          ) : (
            <button
              key={p}
              type="button"
              onClick={() => onPageChange(p)}
              aria-current={p === page ? 'page' : undefined}
              aria-label={`Page ${p}`}
              className={`h-8 min-w-8 rounded-md px-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-primary ${
                p === page ? 'bg-primary text-white' : 'text-secondary hover:bg-slate-100 hover:text-ink'
              }`}
            >
              {p}
            </button>
          ),
        )}
        <button
          type="button"
          className="icon-btn"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </nav>
    </div>
  );
}
