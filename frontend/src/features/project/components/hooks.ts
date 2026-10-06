import { useEffect } from "react";
import { toast } from "@/lib/toast";
import type { ApiError } from "@/lib/api";

export function useErrorToast(error: ApiError | null): void {
  useEffect(() => {
    if (error) toast.error(error.detail);
  }, [error]);
}
