/** Shared UI kit. OWNER: Member 2. Everyone imports these - plan.md 4.5. */

import { createContext, useCallback, useContext, useState } from 'react';

const ToastContext = createContext(null);

const TOAST_TONES = {
  default: '',
  primary: 'border-l-4 border-l-primary-600',
  success: 'border-l-4 border-l-emerald-500',
  warning: 'border-l-4 border-l-amber-500',
  danger: 'border-l-4 border-l-rose-500',
  error: 'border-l-4 border-l-rose-500',
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, tone = 'default', ms = 4000) => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ms);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`card animate-fade-in px-4 py-3 text-sm shadow-lg ${
              TOAST_TONES[t.tone] || ''
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      push: (message, tone = 'default') => {
        console.info(`[Toast ${tone}]: ${message}`);
      },
    };
  }
  return ctx;
}
