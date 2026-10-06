import { AlertTriangle, ShieldCheck } from "lucide-react";
import clsx from "clsx";

export function OriginalityBadge({ originality }: { originality: "original" | "copied" }) {
  const ok = originality === "original";
  const Icon = ok ? ShieldCheck : AlertTriangle;
  return (
    <span className={clsx("badge", ok ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-red-50 text-red-700 ring-red-200")}>
      <Icon className="h-3 w-3" aria-hidden />
      {ok ? "Original" : "Copied"}
    </span>
  );
}
