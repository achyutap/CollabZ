import { ApiError } from "@/lib/api";

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Accepts either a 0-1 fraction or a 0-100 percentage and returns 0-100. */
export function toPct(v: number): number {
  return v <= 1 ? v * 100 : v;
}

export function pctLabel(v: number): string {
  return `${Math.round(toPct(v) * 10) / 10}%`;
}

/** Normalises a quality score (0-1 or 0-100) to 0-1 for ScoreRing. */
export function qualityValue(v: number): number {
  const x = v > 1 ? v / 100 : v;
  return Math.max(0, Math.min(1, x));
}

export function errMsg(e: unknown): string {
  return e instanceof ApiError ? e.detail : "Something went wrong. Please try again.";
}

export function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
