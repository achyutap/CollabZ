"use client";

import { Bell } from "lucide-react";
import clsx from "clsx";
import type { NotificationOut } from "@/lib/types";
import { timeAgo } from "@/components/common";

export function NotificationItem({ n, onOpen }: { n: NotificationOut; onOpen: (n: NotificationOut) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(n)}
      className={clsx("flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-slate-50", !n.is_read && "bg-indigo-50/60")}
    >
      <span className={clsx("mt-0.5 rounded-full p-1.5", n.is_read ? "bg-slate-100 text-slate-400" : "bg-indigo-100 text-indigo-600")}>
        <Bell className="h-3.5 w-3.5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className={clsx("block truncate text-sm", n.is_read ? "text-slate-700" : "font-semibold text-slate-900")}>{n.title}</span>
        <span className="mt-0.5 line-clamp-2 block text-xs text-slate-500">{n.body}</span>
        <span className="mt-1 block text-[11px] text-slate-400">{timeAgo(n.created_at)}</span>
      </span>
      {!n.is_read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-indigo-600" aria-label="Unread" />}
    </button>
  );
}
