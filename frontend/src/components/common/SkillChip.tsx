import { Check, X } from "lucide-react";
import clsx from "clsx";

interface SkillChipProps {
  label: string;
  variant?: "default" | "selected" | "matched" | "missing";
  onClick?: () => void;
  onRemove?: () => void;
}

const VARIANTS: Record<NonNullable<SkillChipProps["variant"]>, string> = {
  default: "bg-slate-100 text-slate-700 ring-slate-200",
  selected: "bg-indigo-600 text-white ring-indigo-600",
  matched: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  missing: "bg-red-50 text-red-700 ring-red-200",
};

export function SkillChip({ label, variant = "default", onClick, onRemove }: SkillChipProps) {
  const cls = clsx(
    "badge px-3 py-1",
    VARIANTS[variant],
    onClick && "cursor-pointer transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
  );
  const content = (
    <>
      {variant === "selected" && <Check className="h-3 w-3" aria-hidden />}
      {label}
    </>
  );
  return (
    <span className="inline-flex items-center">
      {onClick ? (
        <button type="button" onClick={onClick} aria-pressed={variant === "selected"} className={cls}>
          {content}
        </button>
      ) : (
        <span className={cls}>
          {content}
          {onRemove && (
            <button type="button" onClick={onRemove} aria-label={`Remove ${label}`} className="-mr-1 rounded-full p-0.5 hover:bg-black/10">
              <X className="h-3 w-3" />
            </button>
          )}
        </span>
      )}
    </span>
  );
}
