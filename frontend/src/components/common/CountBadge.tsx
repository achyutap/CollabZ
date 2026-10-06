import clsx from "clsx";

export function CountBadge({ count, className }: { count: number; className?: string }) {
  if (!count || count <= 0) return null;
  return (
    <span
      aria-label={`${count} pending`}
      className={clsx("inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-rose-500 px-1.5 text-[11px] font-semibold leading-none text-white", className)}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}
