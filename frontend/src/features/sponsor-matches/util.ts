import { useEffect, useRef } from "react";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

export function msg(e: unknown): string {
  return e instanceof ApiError ? e.detail : "Something went wrong";
}

export function inr(n: number): string {
  return "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);
}

export function useErrorToast(error: ApiError | null | undefined): void {
  const last = useRef<string>("");
  useEffect(() => {
    if (error && error.detail !== last.current) {
      last.current = error.detail;
      toast.error(error.detail);
    }
    if (!error) last.current = "";
  }, [error]);
}
