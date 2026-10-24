import { useCallback, useMemo, useRef, useState } from 'react';
import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { ToastContext } from '../hooks/useToast';

const STYLES = {
  success: { icon: CheckCircle2, className: 'border-teal-200 bg-white', iconClass: 'text-primary' },
  error: { icon: XCircle, className: 'border-red-200 bg-white', iconClass: 'text-red-600' },
  info: { icon: Info, className: 'border-line bg-white', iconClass: 'text-secondary' },
};

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (type, message, title) => {
      const id = nextId.current++;
      setToasts((list) => [...list.slice(-3), { id, type, message, title }]);
      setTimeout(() => dismiss(id), type === 'error' ? 7000 : 4000);
    },
    [dismiss],
  );

  const api = useMemo(
    () => ({
      success: (message, title = 'Success') => push('success', message, title),
      error: (message, title = 'Something went wrong') => push('error', message, title),
      info: (message, title = 'Notice') => push('info', message, title),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-[60] flex flex-col items-end gap-2 sm:inset-x-auto sm:right-6"
      >
        {toasts.map((toast) => {
          const { icon: Icon, className, iconClass } = STYLES[toast.type];
          return (
            <div
              key={toast.id}
              role={toast.type === 'error' ? 'alert' : 'status'}
              className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border p-4 shadow-lg ${className}`}
            >
              <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconClass}`} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{toast.title}</p>
                <p className="mt-0.5 text-sm break-words text-secondary">{toast.message}</p>
              </div>
              <button
                type="button"
                className="icon-btn -m-1 h-7 w-7"
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
