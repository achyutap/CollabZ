import { Star } from "lucide-react";
import clsx from "clsx";

interface StarRatingProps {
  value: number | null;
  size?: "sm" | "md";
  showValue?: boolean;
}

export function StarRating({ value, size = "md", showValue = false }: StarRatingProps) {
  if (value === null || Number.isNaN(value)) {
    return <span className="text-sm text-slate-400">No rating</span>;
  }
  const rounded = Math.round(Math.min(5, Math.max(0, value)) * 2) / 2;
  const px = size === "sm" ? "h-3.5 w-3.5" : "h-5 w-5";
  return (
    <span className="inline-flex items-center gap-1.5" role="img" aria-label={`Rating ${value.toFixed(1)} out of 5`}>
      <span className="inline-flex">
        {[0, 1, 2, 3, 4].map((i) => {
          const fill = Math.min(1, Math.max(0, rounded - i));
          return (
            <span key={i} className={clsx("relative inline-block", px)}>
              <Star className={clsx("absolute inset-0 text-slate-200", px)} aria-hidden />
              {fill > 0 && (
                <span className="absolute inset-y-0 left-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
                  <Star className={clsx("fill-amber-400 text-amber-400", px)} aria-hidden />
                </span>
              )}
            </span>
          );
        })}
      </span>
      {showValue && <span className={clsx("font-semibold text-slate-700", size === "sm" ? "text-xs" : "text-sm")}>{value.toFixed(1)}</span>}
    </span>
  );
}
