import clsx from "clsx";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={clsx("font-bold tracking-tight text-slate-900", className ?? "text-xl")}>
      Collab<span className="bg-gradient-to-r from-indigo-600 to-fuchsia-500 bg-clip-text text-transparent">Z</span>
    </span>
  );
}
