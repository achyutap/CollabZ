"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useCounts } from "@/lib/counts";
import type { NotificationOut } from "@/lib/types";

/** Returns a handler that marks a notification read, refreshes counts and navigates to its link. */
export function useOpenNotification(onDone?: () => void) {
  const router = useRouter();
  const { refresh } = useCounts();
  return useCallback(
    async (n: NotificationOut): Promise<void> => {
      if (!n.is_read) {
        try {
          await api.post<{ ok: boolean }>(`/notifications/${n.id}/read`);
        } catch {
          /* navigation still proceeds */
        }
        refresh();
      }
      onDone?.();
      if (n.link) router.push(n.link);
    },
    [router, refresh, onDone],
  );
}
