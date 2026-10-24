import { useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';
import { useDebounce } from '../hooks/useDebounce';
import { GENDERS, SEMESTERS, STATUSES } from '../types/student';

function FilterSelect({ id, label, value, onChange, children }) {
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="field-input">
        {children}
      </select>
    </div>
  );
}

export default function StudentFilters({ query, options, hasFilters, onChange, onClear }) {
  const [search, setSearch] = useState(query.search);
  const debouncedSearch = useDebounce(search);

  // Keep the input in sync when the URL changes (e.g. "Clear filters" or back button).
  useEffect(() => {
    setSearch(query.search);
  }, [query.search]);

  useEffect(() => {
    if (debouncedSearch.trim() !== query.search) onChange({ search: debouncedSearch.trim() });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  const years = options?.academic_years?.length ? options.academic_years : [1, 2, 3, 4];

  return (
    <div className="flex flex-col gap-3 border-b border-line p-4">
      <div className="relative">
        <label htmlFor="student-search" className="sr-only">
          Search by student ID or name
        </label>
        <Search
          className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        />
        <input
          id="student-search"
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by student ID, Khmer or Latin name…"
          className="field-input pl-9"
          maxLength={100}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <FilterSelect id="filter-gender" label="Gender" value={query.gender} onChange={(v) => onChange({ gender: v })}>
          <option value="">All genders</option>
          {GENDERS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect id="filter-major" label="Major" value={query.major} onChange={(v) => onChange({ major: v })}>
          <option value="">All majors</option>
          {options?.majors?.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          id="filter-year"
          label="Academic year"
          value={query.academic_year}
          onChange={(v) => onChange({ academic_year: v })}
        >
          <option value="">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              Year {y}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          id="filter-semester"
          label="Semester"
          value={query.semester}
          onChange={(v) => onChange({ semester: v })}
        >
          <option value="">All semesters</option>
          {SEMESTERS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect id="filter-status" label="Status" value={query.status} onChange={(v) => onChange({ status: v })}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </FilterSelect>

        <button type="button" className="btn-secondary" onClick={onClear} disabled={!hasFilters}>
          <X className="h-4 w-4" aria-hidden="true" /> Clear filters
        </button>
      </div>
    </div>
  );
}
