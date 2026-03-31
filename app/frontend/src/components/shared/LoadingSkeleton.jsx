/**
 * LoadingSkeleton — reusable shimmer placeholder for async content.
 * Usage:
 *   <LoadingSkeleton className="h-8 w-32 rounded-lg" />
 *   <LoadingSkeleton lines={3} />
 */
export default function LoadingSkeleton({ className = '', lines = 0 }) {
  if (lines > 0) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`animate-pulse rounded-md bg-white/5 h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`animate-pulse rounded-md bg-white/5 ${className}`} />
  );
}

/**
 * CardSkeleton — full metric card placeholder.
 */
export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/5 bg-[#10151a] p-4 shadow-[0_8px_24px_rgba(0,0,0,0.18)]">
      <LoadingSkeleton className="h-3 w-20 mb-3" />
      <LoadingSkeleton className="h-7 w-28 mb-2" />
      <LoadingSkeleton className="h-3 w-16" />
    </div>
  );
}

/**
 * TableRowSkeleton — placeholder for a table/list row.
 */
export function TableRowSkeleton({ cols = 4 }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5">
      {Array.from({ length: cols }).map((_, i) => (
        <LoadingSkeleton key={i} className={`h-3 flex-1 ${i === 0 ? 'max-w-[60px]' : ''}`} />
      ))}
    </div>
  );
}
