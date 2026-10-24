import { AlertCircle, Inbox, Loader2, RefreshCw } from 'lucide-react';

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-3 py-16 text-secondary">
      <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function EmptyState({ title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
        <Inbox className="h-6 w-6 text-secondary" aria-hidden="true" />
      </span>
      <h3 className="mt-2 text-base font-semibold text-ink">{title}</h3>
      {message && <p className="max-w-sm text-sm text-secondary">{message}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-2 px-4 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
        <AlertCircle className="h-6 w-6 text-red-600" aria-hidden="true" />
      </span>
      <h3 className="mt-2 text-base font-semibold text-ink">Could not load data</h3>
      <p className="max-w-md text-sm text-secondary">
        {error?.message || 'An unexpected error occurred.'}
      </p>
      {onRetry && (
        <button type="button" className="btn-secondary mt-3" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  );
}
