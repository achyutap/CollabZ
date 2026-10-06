"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { ActivityItem, FileOut, ProjectDetail, SubmissionOut } from "@/lib/types";
import { EmptyState, FileExplorer, Spinner, StarRating, Timeline, UserAvatar } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import SubmissionCard from "./SubmissionCard";
import { downloadFile, loadContent, loadVersions } from "./fileApi";
import { useErrorToast } from "./hooks";
import { isProjectResearcher } from "./tabTypes";

interface Props {
  projectId: string;
  project: ProjectDetail;
  memberId: string;
  onBack: () => void;
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-center">
      <p className="text-xl font-semibold text-slate-900">{value}</p>
      <p className="help">{label}</p>
    </div>
  );
}

export default function MemberView({ projectId, project, memberId, onBack }: Props) {
  const subs = useFetch<SubmissionOut[]>(`/projects/${projectId}/submissions`, { params: { student_id: memberId } });
  const activity = useFetch<ActivityItem[]>(`/projects/${projectId}/activity`, {
    params: { user_id: memberId, limit: "100" },
  });
  const files = useFetch<FileOut[]>(`/projects/${projectId}/files`);
  useErrorToast(subs.error);
  useErrorToast(activity.error);
  useErrorToast(files.error);

  const researcher = project.researchers.find((r) => r.id === memberId);
  const student = project.members.find((m) => m.student_id === memberId);
  const mySubs = (subs.data ?? []).filter((s) => s.student_id === memberId);
  const actorName = (activity.data ?? []).find((a) => a.actor?.id === memberId)?.actor?.name;
  const name = researcher?.name ?? student?.name ?? mySubs[0]?.student_name ?? actorName ?? "Team member";
  const roleLabel = researcher
    ? researcher.role === "lead"
      ? "Lead researcher"
      : "Researcher"
    : student
    ? `Student · ${skillLabel(student.skill)}`
    : "Former team member";

  const theirFiles = (files.data ?? []).filter((f) => f.author_id === memberId);
  const approved = mySubs.filter((s) => s.status === "approved").length;
  const pending = mySubs.filter((s) => s.status === "pending").length;
  const viewerResearcher = isProjectResearcher(project);
  const viewerSponsor = project.my_role === "sponsor";

  return (
    <div className="space-y-6">
      <button type="button" onClick={onBack} className="btn btn-ghost btn-sm">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to team
      </button>

      <section className="card space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <UserAvatar name={name} size="lg" />
          <div className="min-w-0 flex-1">
            <h2 className="section-title">{name}</h2>
            <p className="muted">{roleLabel}</p>
            {student && <StarRating value={student.rating} size="sm" showValue />}
          </div>
          <Link href={`/profile/${memberId}`} className="btn btn-secondary btn-sm">View profile</Link>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Submitted" value={mySubs.length} />
          <Stat label="Approved" value={approved} />
          <Stat label="Pending" value={pending} />
          <Stat label="Files" value={theirFiles.length} />
        </div>
      </section>

      <section className="card space-y-3">
        <h3 className="section-title">Activity</h3>
        {activity.loading && !activity.data ? (
          <Spinner />
        ) : (
          <Timeline items={activity.data ?? []} emptyText="No activity from this person yet." />
        )}
      </section>

      <section className="space-y-3">
        <h3 className="section-title">Submissions</h3>
        {subs.loading && !subs.data ? (
          <Spinner />
        ) : mySubs.length === 0 ? (
          <EmptyState title="No submissions" description="This person hasn't submitted work in this project." />
        ) : (
          mySubs.map((s) => (
            <SubmissionCard key={s.id} submission={s} isResearcher={viewerResearcher} isSponsor={viewerSponsor} />
          ))
        )}
      </section>

      <section className="card space-y-3">
        <h3 className="section-title">Files</h3>
        {files.loading && !files.data ? (
          <Spinner />
        ) : (
          <FileExplorer
            files={theirFiles}
            loadContent={loadContent}
            loadVersions={loadVersions}
            onDownload={downloadFile}
            emptyText="No files from this person yet."
          />
        )}
      </section>
    </div>
  );
}
