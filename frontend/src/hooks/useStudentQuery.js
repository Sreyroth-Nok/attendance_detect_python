import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

const FILTER_KEYS = ['search', 'gender', 'major', 'academic_year', 'semester', 'status'];
const DEFAULTS = { page: 1, page_size: 20, sort_by: 'full_name_latin', sort_order: 'asc' };

/**
 * Keeps the student list's search, filters, sorting and page in the URL so the view
 * survives reloads, works with the back button and can be shared.
 */
export function useStudentQuery() {
  const [searchParams, setSearchParams] = useSearchParams();

  const query = useMemo(() => {
    const q = {
      page: Number(searchParams.get('page')) || DEFAULTS.page,
      page_size: Number(searchParams.get('page_size')) || DEFAULTS.page_size,
      sort_by: searchParams.get('sort_by') || DEFAULTS.sort_by,
      sort_order: searchParams.get('sort_order') === 'desc' ? 'desc' : 'asc',
    };
    FILTER_KEYS.forEach((key) => {
      q[key] = searchParams.get(key) || '';
    });
    return q;
  }, [searchParams]);

  const update = useCallback(
    (changes, { resetPage = true } = {}) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          Object.entries(changes).forEach(([key, value]) => {
            if (value === '' || value == null || value === DEFAULTS[key]) next.delete(key);
            else next.set(key, String(value));
          });
          if (resetPage && !('page' in changes)) next.delete('page');
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const clearFilters = useCallback(() => {
    update(Object.fromEntries(FILTER_KEYS.map((k) => [k, ''])));
  }, [update]);

  const filters = useMemo(
    () => Object.fromEntries(FILTER_KEYS.map((k) => [k, query[k]])),
    [query],
  );
  const hasFilters = FILTER_KEYS.some((k) => query[k]);

  return { query, filters, hasFilters, update, clearFilters };
}
