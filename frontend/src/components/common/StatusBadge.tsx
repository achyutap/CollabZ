import clsx from "clsx";

const GREEN = "bg-emerald-50 text-emerald-700 ring-emerald-200";
const RED = "bg-red-50 text-red-700 ring-red-200";
const AMBER = "bg-amber-50 text-amber-700 ring-amber-200";
const SLATE = "bg-slate-100 text-slate-600 ring-slate-200";
const INDIGO = "bg-indigo-50 text-indigo-700 ring-indigo-200";
const VIOLET = "bg-violet-50 text-violet-700 ring-violet-200";

const MAP: Record<string, { label: string; cls: string }> = {
  open: { label: "Open", cls: "bg-sky-50 text-sky-700 ring-sky-200" },
  matched: { label: "Matched", cls: VIOLET },
  completed: { label: "Completed", cls: GREEN },
  pending: { label: "Pending", cls: AMBER },
  accepted: { label: "Accepted", cls: GREEN },
  declined: { label: "Declined", cls: RED },
  expired: { label: "Expired", cls: SLATE },
  active: { label: "Active", cls: INDIGO },
  approved: { label: "Approved", cls: GREEN },
  rejected: { label: "Rejected", cls: RED },
  clean: { label: "Clean", cls: GREEN },
  suspicious: { label: "Suspicious", cls: AMBER },
  likely_copied: { label: "Likely copied", cls: RED },
  copied: { label: "Copied", cls: RED },
  original: { label: "Original", cls: GREEN },
  removed: { label: "Removed", cls: "bg-orange-50 text-orange-700 ring-orange-200" },
  blacklisted: { label: "Blacklisted", cls: "bg-red-100 text-red-800 ring-red-300" },
  lead: { label: "Lead", cls: INDIGO },
  researcher: { label: "Researcher", cls: VIOLET },
};

export function StatusBadge({ status }: { status: string }) {
  const entry = MAP[status] ?? {
    label: status.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()),
    cls: SLATE,
  };
  return <span className={clsx("badge", entry.cls)}>{entry.label}</span>;
}
