"use client";

import { createContext, useCallback, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { useFetch } from "@/lib/hooks";
import type { CountsOut } from "@/lib/types";

interface CountsContextValue {
  counts: CountsOut | undefined;
  refresh: () => void;
}

const CountsContext = createContext<CountsContextValue>({ counts: undefined, refresh: () => undefined });

export function CountsProvider({ children }: { children: ReactNode }) {
  const { data, refetch } = useFetch<CountsOut>("/me/counts", { intervalMs: 20000 });
  const refresh = useCallback(() => {
    void refetch();
  }, [refetch]);
  const value = useMemo(() => ({ counts: data, refresh }), [data, refresh]);
  return <CountsContext.Provider value={value}>{children}</CountsContext.Provider>;
}

export function useCounts(): CountsContextValue {
  return useContext(CountsContext);
}
