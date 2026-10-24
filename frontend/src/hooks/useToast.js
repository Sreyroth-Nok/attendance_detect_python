import { createContext, useContext } from 'react';

export const ToastContext = createContext(null);

/** @returns {{ success: (msg: string, title?: string) => void, error: (msg: string, title?: string) => void, info: (msg: string, title?: string) => void }} */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}
