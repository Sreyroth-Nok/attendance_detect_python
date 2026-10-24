import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

/** Page title, breadcrumb trail and optional action buttons. */
export default function PageHeader({ title, breadcrumbs = [], actions, description }) {
  useEffect(() => {
    document.title = `${title} · Student Management`;
  }, [title]);

  return (
    <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-1 text-sm text-secondary">
            <li>
              <Link to="/" className="hover:text-primary">
                Home
              </Link>
            </li>
            {breadcrumbs.map((crumb, index) => {
              const last = index === breadcrumbs.length - 1;
              return (
                <li key={crumb.label} className="flex items-center gap-1">
                  <ChevronRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
                  {crumb.to && !last ? (
                    <Link to={crumb.to} className="hover:text-primary">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span aria-current={last ? 'page' : undefined} className={last ? 'text-ink' : ''}>
                      {crumb.label}
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
