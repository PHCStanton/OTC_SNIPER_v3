/**
 * ToastContainer — renders the global toast notification queue.
 * Positioned bottom-right, stacks upward. Redesigned for Stitch.
 */
import { useEffect, useState, useRef } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToastStore } from '../../stores/useToastStore.js';

const TOAST_STYLES = {
  success: {
    container: 'border-emerald-500/25 bg-[#0d2318] text-emerald-400',
    icon: CheckCircle2,
    iconClass: 'text-emerald-400',
  },
  error: {
    container: 'border-red-500/25 bg-[#2a0d0d] text-red-400',
    icon: XCircle,
    iconClass: 'text-red-400',
  },
  warning: {
    container: 'border-[#ffb800]/25 bg-[#ffb800]/5 text-[#ffb800]',
    icon: AlertTriangle,
    iconClass: 'text-[#ffb800]',
  },
  info: {
    container: 'border-sky-500/25 bg-[#0d1a2a] text-sky-400',
    icon: Info,
    iconClass: 'text-sky-400',
  },
};

/**
 * Individual Toast Item with sustain-on-hover support.
 */
function ToastItem({ toast, onRemove }) {
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef(null);

  const style = TOAST_STYLES[toast.type] ?? TOAST_STYLES.info;
  const Icon = style.icon;

  useEffect(() => {
    // If duration is <= 0, it's a persistent toast
    if (!toast.duration || toast.duration <= 0) return;

    if (isHovered) {
      // Clear timer while hovering
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    } else {
      // Set/Resume timer when not hovering
      timerRef.current = setTimeout(() => {
        onRemove(toast.id);
      }, toast.duration);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isHovered, toast.id, toast.duration, onRemove]);

  return (
    <div
      role="alert"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onDoubleClick={() => {
        if (toast.onDoubleClick) toast.onDoubleClick();
      }}
      className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4.5 py-3.5 shadow-2xl shadow-black/50 backdrop-blur-md min-w-[260px] max-w-[380px] animate-in slide-in-from-right-4 fade-in duration-200 transition-all ${
        toast.onDoubleClick 
          ? 'cursor-pointer hover:border-[#ffb800]/50 hover:shadow-[#ffb800]/5' 
          : ''
      } ${style.container} ${isHovered ? 'scale-[1.02] border-opacity-60' : ''}`}
    >
      <Icon size={14} className={`mt-0.5 shrink-0 ${style.iconClass}`} />
      <p className="flex-1 text-[10px] font-black uppercase tracking-wider leading-relaxed">{toast.message}</p>
      <button
        type="button"
        onClick={() => onRemove(toast.id)}
        className="shrink-0 rounded p-0.5 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        <X size={13} />
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-6 right-6 z-[9999] flex flex-col-reverse gap-2.5 pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
}
