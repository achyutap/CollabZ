import type { ReactNode } from "react";
import { Activity, CheckCircle2, EyeOff, Flag, FlaskConical, Globe, Rocket, Upload, UserMinus, UserPlus, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";
import type { ActivityItem } from "@/lib/types";
import { UserAvatar } from "./UserAvatar";
import { StatusBadge } from "./StatusBadge";
import { timeAgo } from "./format";

interface TimelineProps {
  items: ActivityItem[];
  onActorClick?: (actorId: string) => void;
  emptyText?: string;
}

const ICONS: Record<string, { icon: LucideIcon; cls: string }> = {
  project_created: { icon: Rocket, cls: "bg-indigo-50 text-indigo-600" },
  researcher_joined: { icon: FlaskConical, cls: "bg-violet-50 text-violet-600" },
  student_joined: { icon: UserPlus, cls: "bg-sky-50 text-sky-600" },
  student_removed: { icon: UserMinus, cls: "bg-orange-50 text-orange-600" },
  submission_created: { icon: Upload, cls: "bg-slate-100 text-slate-600" },
  submission_approved: { icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-600" },
  submission_rejected: { icon: XCircle, cls: "bg-red-50 text-red-600" },
  files_published: { icon: Globe, cls: "bg-emerald-50 text-emerald-600" },
  files_unpublished: { icon: EyeOff, cls: "bg-slate-100 text-slate-500" },
  project_completed: { icon: Flag, cls: "bg-amber-50 text-amber-600" },
};

function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

export function Timeline({ items, onActorClick, emptyText = "No activity yet." }: TimelineProps) {
  if (items.length === 0) return <p className="muted py-6 text-center">{emptyText}</p>;
  return (
    <ol className="relative">
      {items.map((it, idx) => {
        const conf = ICONS[it.type] ?? { icon: Activity, cls: "bg-slate-100 text-slate-500" };
        const Icon = conf.icon;
        const isSubmission = it.type.startsWith("submission_");
        const commit = str(it.meta.commit_msg);
        const fileCount = typeof it.meta.file_count === "number" ? it.meta.file_count : null;
        const status = str(it.meta.status);
        let actor: ReactNode = null;
        if (it.actor) {
          const a = it.actor;
          actor = onActorClick ? (
            <button type="button" onClick={() => onActorClick(a.id)} className="inline-flex items-center gap-1.5 font-medium text-slate-900 hover:text-indigo-600">
              <UserAvatar name={a.name} size="sm" />
              {a.name}
            </button>
          ) : (
            <span className="inline-flex items-center gap-1.5 font-medium text-slate-900">
              <UserAvatar name={a.name} size="sm" />
              {a.name}
            </span>
          );
        }
        return (
          <li key={it.id} className="relative flex gap-3 pb-6 last:pb-0">
            {idx < items.length - 1 && <span className="absolute left-4 top-9 -ml-px h-[calc(100%-2rem)] w-px bg-slate-200" aria-hidden />}
            <span className={clsx("relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full", conf.cls)}>
              <Icon className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 pt-0.5">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                {actor}
                <span className="text-slate-600">{it.message}</span>
              </div>
              {isSubmission && (commit || fileCount !== null) && (
                <div className="mt-1.5 flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  {commit && <span className="font-medium text-slate-800">{commit}</span>}
                  {fileCount !== null && (
                    <span>
                      {fileCount} file{fileCount === 1 ? "" : "s"}
                    </span>
                  )}
                  {status && <StatusBadge status={status} />}
                </div>
              )}
              <p className="mt-1 text-xs text-slate-400">{timeAgo(it.created_at)}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
