import clsx from "clsx";

const GRADIENTS = [
  "from-indigo-500 to-violet-500",
  "from-emerald-500 to-teal-500",
  "from-amber-500 to-orange-500",
  "from-rose-500 to-pink-500",
  "from-sky-500 to-indigo-500",
  "from-fuchsia-500 to-purple-500",
];

export function UserAvatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const initials = ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  const dim = size === "sm" ? "h-7 w-7 text-xs" : size === "lg" ? "h-14 w-14 text-lg" : "h-9 w-9 text-sm";
  return (
    <span aria-hidden className={clsx("inline-flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-semibold text-white", dim, GRADIENTS[hash % GRADIENTS.length])}>
      {initials}
    </span>
  );
}
