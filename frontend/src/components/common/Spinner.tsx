import { Loader2 } from "lucide-react";
import clsx from "clsx";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 role="status" aria-label="Loading" className={clsx("h-6 w-6 animate-spin text-indigo-600", className)} />;
}
