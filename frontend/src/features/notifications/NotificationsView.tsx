"use client";

import { useEffect, useState } from "react";
import { CheckCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCounts } from "@/lib/counts";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { NotificationOut } from "@/lib/types";
import { EmptyState, PageHeader, Spinner, Tabs } from "@/components/common";
import { NotificationItem } from "./NotificationItem";
import { useOpenNotification } from "./useOpenNotification";

export default function NotificationsView() {
  const { counts, refresh } = useCounts();
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const { data, loading, error, refetch } = useFetch<NotificationOut[]>("/notifications", {
    params: { unread_only: filter === "unread" ? "true" : undefined },
  });
  const openNotification = useOpenNotification();
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    if (error) toast.error(error.detail);
  }, [error]);

  const markAll = async () => {
    setMarking(true);
    try {
      await api.post<{ ok: boolean }>("/notifications/read-all");
      await refetch();
      refresh();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Could not update notifications");
    } finally {
      setMarking(false);
    }
  };

  const unread = counts?.notifications ?? 0;

  return (
    <div className="page">
      <PageHeader
        title="Notifications"
        description="Updates about your requests, projects and work."
        actions={
          <button type="button" onClick={markAll} disabled={marking || unread === 0} className="btn btn-secondary btn-sm">
            <CheckCheck className="h-4 w-4" aria-hidden /> Mark all read
          </button>
        }
      />
      <Tabs
        tabs={[
          { id: "all", label: "All" },
          { id: "unread", label: "Unread", count: unread },
        ]}
        active={filter}
        onChange={(id) => setFilter(id === "unread" ? "unread" : "all")}
      />
      {loading && !data ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : !data || data.length === 0 ? (
        <EmptyState title={filter === "unread" ? "No unread notifications" : "No notifications yet"} description="New activity will show up here." />
      ) : (
        <div className="card divide-y divide-slate-100 overflow-hidden !p-0">
          {data.map((n) => (
            <NotificationItem key={n.id} n={n} onOpen={openNotification} />
          ))}
        </div>
      )}
    </div>
  );
}
