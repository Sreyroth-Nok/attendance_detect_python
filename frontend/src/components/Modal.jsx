import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

const SIZES = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl' };

/**
 * Accessible modal built on the native <dialog> element, which provides focus
 * trapping, Escape-to-close and an inert background for free.
 */
export default function Modal({ open, onClose, title, description, size = 'md', children, footer }) {
  const ref = useRef(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const handleCancel = (event) => {
    event.preventDefault(); // keep React in control of the open state
    onClose?.();
  };

  const handleBackdropClick = (event) => {
    if (event.target === ref.current) onClose?.();
  };

  return (
    <dialog
      ref={ref}
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      className={`m-auto w-[calc(100%-2rem)] ${SIZES[size]} rounded-2xl border border-line bg-white p-0 text-ink shadow-xl`}
    >
      {open && (
        <div className="flex max-h-[85vh] flex-col">
          <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
            <div>
              <h2 id={titleId} className="text-lg font-semibold text-ink">
                {title}
              </h2>
              {description && (
                <p id={descId} className="mt-1 text-sm text-secondary">
                  {description}
                </p>
              )}
            </div>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Close dialog">
              <X className="h-5 w-5" />
            </button>
          </header>
          <div className="overflow-y-auto px-6 py-5">{children}</div>
          {footer && (
            <footer className="flex flex-col-reverse gap-2 border-t border-line px-6 py-4 sm:flex-row sm:justify-end">
              {footer}
            </footer>
          )}
        </div>
      )}
    </dialog>
  );
}
