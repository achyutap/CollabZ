"use client";
import Link from "next/link";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { FileContent, FileOut, PublicProjectDetail } from "@/lib/types";
import { StatusBadge, SkillChip, EmptyState, FileExplorer, UserAvatar, Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { formatDate } from "@/components/common/format";
import { msg, useErrorToast } from "./util";
import { toast } from "@/lib/toast";

export default function PublicProjectPage({ projectId }: { projectId: string }) {
  const { data, error, loading } = useFetch<PublicProjectDetail>(`/explore/projects/${projectId}`);
  useErrorToast(error);
  if (loading && !data) return <div className="page flex justify-center py-16"><Spinner /></div>;
  if (!data) return <div className="page"><EmptyState title="Project not available" description="It may not have any public files." action={<Link href="/explore" className="btn btn-secondary">Back to Explore</Link>} /></div>;

  return (
    <div className="page">
      <section className="card space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-2xl font-semibold text-slate-900">{data.title}</h1>
          <StatusBadge status={data.status} />
        </div>
        <div className="flex flex-wrap gap-1.5">{data.required_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} />)}</div>
        <p className="muted text-xs">Sponsored by {data.sponsor_name} · Started {formatDate(data.started_at)}{data.completed_at ? ` · Completed ${formatDate(data.completed_at)}` : ""}</p>
      </section>

      <section className="card space-y-2 p-5" aria-label="Description">
        <h2 className="section-title">Description</h2>
        <p className="whitespace-pre-line text-sm text-slate-700">{data.description}</p>
      </section>

      <section className="card space-y-4 p-5" aria-label="Team">
        <h2 className="section-title">Team</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.researchers.map((r) => (
            <li key={r.id} className="flex items-center gap-3">
              <UserAvatar name={r.name} />
              <div className="min-w-0">
                <Link href={`/profile/${r.id}`} className="block truncate text-sm font-medium hover:underline">{r.name}</Link>
                <p className="muted truncate text-xs">{r.headline}</p>
              </div>
              <span className="badge">{r.role === "lead" ? "Lead" : "Researcher"}</span>
            </li>
          ))}
          {data.members.map((m) => (
            <li key={m.id} className="flex items-center gap-3">
              <UserAvatar name={m.name} />
              <Link href={`/profile/${m.id}`} className="flex-1 truncate text-sm font-medium hover:underline">{m.name}</Link>
              {m.skill && <SkillChip label={skillLabel(m.skill)} />}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3" aria-label="Public files">
        <h2 className="section-title">Public files</h2>
        <FileExplorer
          files={data.files}
          emptyText="No public files."
          loadContent={(f: FileOut) => api.get<FileContent>(`/files/${f.id}/content`)}
          loadVersions={(f: FileOut) => api.get<FileOut[]>(`/files/${f.id}/versions`)}
          onDownload={(f: FileOut) => { api.download(`/files/${f.id}/download`, f.name).catch((e: unknown) => toast.error(msg(e))); }}
        />
      </section>
    </div>
  );
}
