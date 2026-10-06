"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";

interface UseFetchOptions {
  params?: Record<string, string | undefined>;
  intervalMs?: number;
}

interface UseFetchResult<T> {
  data: T | undefined;
  error: ApiError | null;
  loading: boolean;
  refetch: () => Promise<void>;
}

export function useFetch<T>(path: string | null, opts?: UseFetchOptions): UseFetchResult<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const mounted = useRef(true);
  const requestId = useRef(0);

  const paramsKey = JSON.stringify(opts?.params ?? {});
  const intervalMs = opts?.intervalMs;

  const run = useCallback(
    async (silent: boolean): Promise<void> => {
      if (path === null) return;
      const id = ++requestId.current;
      if (!silent) setLoading(true);
      try {
        const params = JSON.parse(paramsKey) as Record<string, string | undefined>;
        const res = await api.get<T>(path, params);
        if (!mounted.current || id !== requestId.current) return;
        setData(res);
        setError(null);
      } catch (e) {
        if (!mounted.current || id !== requestId.current) return;
        setError(e instanceof ApiError ? e : new ApiError(0, "ERROR", "Something went wrong"));
      } finally {
        if (mounted.current && id === requestId.current && !silent) setLoading(false);
      }
    },
    [path, paramsKey],
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (path === null) {
      setLoading(false);
      return;
    }
    void run(false);
    if (!intervalMs || intervalMs <= 0) return;
    const timer = setInterval(() => {
      void run(true);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [path, run, intervalMs]);

  const refetch = useCallback(() => run(true), [run]);

  return { data, error, loading, refetch };
}
