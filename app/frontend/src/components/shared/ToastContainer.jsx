/**
 * ToastContainer — renders the global toast notification queue.
 * Positioned bottom-right, stacks upward.
 * Driven by useToastStore.
 */
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToastStore } from '../../stores/useToastStore.js';

const TOAST_STYLES = {
  success: {
    container: 'border-emerald-500/30 bg-[#0d2318] text-emerald-300',
    icon: CheckCircle2,
    iconClass: 'text-emerald-400',
  },
  error: {
    container: 'border-red-500/30 bg-[#2a0d0d] text-red-300',
    icon: XCircle,
    iconClass: 'text-red-400',
  },
  warning: {
    container: 'border-[#f5df19]/30 bg-[#1f1a00] text-[#f5df19]',
    icon: AlertTriangle,
    iconClass: 'text-[#f5df19]',
  },
  info: {
    container: 'border-sky-500/30 bg-[#0d1a2a] text-sky-300',
    icon: Info,
    iconClass: 'text-sky-400',
  },
};

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 pointer-events-none"
    >
      {toasts.map((toast) => {
        const style = TOAST_STYLES[toast.type] ?? TOAST_STYLES.info;
        const Icon = style.icon;

        return (
          <div
            key={toast.id}
            role="alert"
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl shadow-black/40 backdrop-blur-sm min-w-[260px] max-w-[380px] animate-in slide-in-from-right-4 fade-in duration-200 ${style.container}`}
          >
            <Icon size={16} className={`mt-0.5 shrink-0 ${style.iconClass}`} />
            <p className="flex-1 text-sm font-medium leading-snug">{toast.message}</p>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="shrink-0 rounded p-0.5 opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Dismiss notification"
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
