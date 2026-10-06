"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCounts } from "@/lib/counts";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { NotificationOut } from "@/lib/types";
import { CountBadge, Spinner } from "@/components/common";
import { NotificationItem } from "./NotificationItem";
import { useOpenNotification } from "./useOpenNotification";

export function NotificationBell() {
  const { counts, refresh } = useCounts();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const { data, loading, error, refetch } = useFetch<NotificationOut[]>(open ? "/notifications" : null);
  const close = useCallback(() => setOpen(false), []);
  const openNotification = useOpenNotification(close);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    if (error) toast.error(error.detail);
  }, [error]);

  const markAll = async () => {
    try {
      await api.post<{ ok: boolean }>("/notifications/read-all");
      await refetch();
      refresh();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Could not update notifications");
    }
  };

  const unread = counts?.notifications ?? 0;
  const items = (data ?? []).slice(0, 8);

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        aria-haspopup="true"
        aria-expanded={open}
        className="btn btn-ghost relative !p-2"
      >
        <Bell className="h-5 w-5" aria-hidden />
        <CountBadge count={unread} className="absolute -right-0.5 -top-0.5" />
      </button>
      {open && (
        <div className="fixed inset-x-3 top-16 z-50 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-2 sm:w-96">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
            <button type="button" onClick={markAll} disabled={unread === 0} className="text-xs font-medium text-indigo-600 hover:underline disabled:text-slate-400 disabled:no-underline">
              Mark all read
            </button>
          </div>
          <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
            {loading && !data ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : items.length === 0 ? (
              <p className="muted px-4 py-8 text-center">You&apos;re all caught up.</p>
            ) : (
              items.map((n) => <NotificationItem key={n.id} n={n} onOpen={openNotification} />)
            )}
          </div>
          <Link href="/notifications" onClick={close} className="block border-t border-slate-100 px-4 py-2.5 text-center text-sm font-medium text-indigo-600 hover:bg-slate-50">
            View all
          </Link>
        </div>
      )}
    </div>
  );
}
