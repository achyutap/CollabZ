"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Github, Globe, GraduationCap, Heart, Linkedin, MapPin, Pencil } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { ProfileOut } from "@/lib/types";
import { StarRating, StatusBadge, SkillChip, EmptyState, UserAvatar, Spinner } from "@/components/common";
import { SKILLS, skillLabel } from "@/components/common/skills";
import { formatDate } from "@/components/common/format";
import DetailSection from "./DetailSection";
import type { SectionCfg } from "./DetailSection";
import WalletCard from "./WalletCard";
import { msg, useErrorToast } from "./util";

type Details = Record<string, unknown>;
type LikeOut = { likes_count: number; liked_by_me: boolean };
type IntegrityItem = { id: string; action: string; detail: string; created_at: string };

const EDU = [
  { key: "school", label: "School" }, { key: "degree", label: "Degree" }, { key: "field", label: "Field" },
  { key: "start_year", label: "Start year" }, { key: "end_year", label: "End year" },
];
const SECTIONS: Record<string, SectionCfg[]> = {
  student: [
    { kind: "rows", title: "Education", key: "education", fields: EDU, addLabel: "Add education" },
    { kind: "rows", title: "Experience", key: "experience", fields: [{ key: "title", label: "Title" }, { key: "org", label: "Organization" }, { key: "description", label: "Description" }, { key: "start", label: "Start" }, { key: "end", label: "End" }], addLabel: "Add experience" },
    { kind: "tags", title: "Achievements", key: "achievements", placeholder: "Add an achievement" },
    { kind: "tags", title: "Interests", key: "interests", placeholder: "Add an interest" },
  ],
  researcher: [
    { kind: "fields", title: "Affiliation", fields: [{ key: "institution", label: "Institution" }, { key: "department", label: "Department" }, { key: "designation", label: "Designation" }] },
    { kind: "tags", title: "Research areas", key: "research_areas", placeholder: "Add a research area" },
    { kind: "rows", title: "Publications", key: "publications", fields: [{ key: "title", label: "Title" }, { key: "venue", label: "Venue" }, { key: "year", label: "Year" }, { key: "url", label: "URL" }], addLabel: "Add publication" },
    { kind: "rows", title: "Education", key: "education", fields: EDU, addLabel: "Add education" },
    { kind: "tags", title: "Awards", key: "awards", placeholder: "Add an award" },
  ],
  sponsor: [
    { kind: "fields", title: "Organization", fields: [{ key: "organization", label: "Organization" }, { key: "industry", label: "Industry" }, { key: "website", label: "Website" }] },
    { kind: "tags", title: "Focus areas", key: "focus_areas", placeholder: "Add a focus area" },
  ],
};
const LINKS: { key: "github" | "linkedin" | "website" | "scholar"; label: string }[] = [
  { key: "github", label: "GitHub" }, { key: "linkedin", label: "LinkedIn" }, { key: "website", label: "Website" }, { key: "scholar", label: "Google Scholar" },
];
const URL_RE = /^https?:\/\/\S+$/i;

function LinkIcon({ k }: { k: string }) {
  const c = "h-5 w-5";
  return k === "github" ? <Github className={c} /> : k === "linkedin" ? <Linkedin className={c} /> : k === "scholar" ? <GraduationCap className={c} /> : <Globe className={c} />;
}

export default function ProfileView({ userId }: { userId?: string }) {
  const { refreshUser } = useAuth();
  const { data, error, loading } = useFetch<ProfileOut>(userId ? `/users/${userId}/profile` : "/me/profile");
  useErrorToast(error);
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [like, setLike] = useState<LikeOut | null>(null);
  const [editHead, setEditHead] = useState(false);
  const [editAbout, setEditAbout] = useState(false);
  const [editSkills, setEditSkills] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({ name: "", headline: "", location: "", github: "", linkedin: "", website: "", scholar: "" });
  const [aboutDraft, setAboutDraft] = useState("");
  const [skillToAdd, setSkillToAdd] = useState("");
  const [linkErr, setLinkErr] = useState("");

  useEffect(() => { if (data) { setProfile(data); setLike({ likes_count: data.likes_count, liked_by_me: data.liked_by_me }); } }, [data]);
  const integrity = useFetch<IntegrityItem[]>(profile?.is_me ? "/me/integrity" : null);

  async function patch(body: Record<string, unknown>): Promise<boolean> {
    try {
      const p = await api.patch<ProfileOut>("/me/profile", body);
      setProfile(p);
      toast.success("Profile updated");
      await refreshUser();
      return true;
    } catch (e) { toast.error(msg(e)); return false; }
  }

  if (loading && !profile) return <div className="page flex justify-center py-16"><Spinner /></div>;
  if (!profile) return <div className="page"><EmptyState title="Profile not found" /></div>;

  const p = profile;
  const isMe = p.is_me;
  const role = p.user.role;
  const details = (p.details ?? {}) as Details;
  const links = p.links ?? {};
  const likeState = like ?? { likes_count: p.likes_count, liked_by_me: p.liked_by_me };
  const hasRating = role === "student" || role === "researcher";

  async function toggleLike() {
    const prev = likeState;
    setLike({ likes_count: prev.likes_count + (prev.liked_by_me ? -1 : 1), liked_by_me: !prev.liked_by_me });
    try {
      const r = prev.liked_by_me ? await api.delete<LikeOut>(`/users/${p.user.id}/like`) : await api.post<LikeOut>(`/users/${p.user.id}/like`);
      setLike(r);
    } catch (e) { setLike(prev); toast.error(msg(e)); }
  }

  function startHead() {
    setDraft({ name: p.user.name, headline: p.headline ?? "", location: p.location ?? "", github: links.github ?? "", linkedin: links.linkedin ?? "", website: links.website ?? "", scholar: links.scholar ?? "" });
    setLinkErr("");
    setEditHead(true);
  }
  async function saveHead() {
    if (draft.name.trim().length < 1) { setLinkErr("Name is required."); return; }
    if (draft.headline.length > 120) { setLinkErr("Headline must be 120 characters or fewer."); return; }
    const out: Record<string, string> = {};
    for (const l of LINKS) {
      const v = draft[l.key].trim();
      if (v && !URL_RE.test(v)) { setLinkErr(`${l.label} must be a valid http(s) URL.`); return; }
      if (v) out[l.key] = v;
    }
    setSaving(true);
    const ok = await patch({ name: draft.name.trim(), headline: draft.headline.trim(), location: draft.location.trim(), links: out });
    setSaving(false);
    if (ok) setEditHead(false);
  }
  async function saveAbout() {
    if (aboutDraft.length > 2000) { toast.error("About must be 2000 characters or fewer."); return; }
    setSaving(true);
    const ok = await patch({ about: aboutDraft });
    setSaving(false);
    if (ok) setEditAbout(false);
  }

  const allSkills = [...p.skills, ...(p.pending_skills ?? [])];
  const availableSkills = SKILLS.filter((s) => !allSkills.includes(s.id));
  const canEditSkills = isMe && role !== "sponsor";

  return (
    <div className="page space-y-6">
      <section className="card overflow-hidden" aria-label="Profile header">
        <div className="h-28 bg-gradient-to-r from-indigo-500 via-violet-500 to-sky-400 sm:h-36" />
        <div className="space-y-3 px-5 pb-5">
          <div className="-mt-12 flex flex-wrap items-end justify-between gap-3">
            <div className="rounded-full border-4 border-white bg-white"><UserAvatar name={p.user.name} size="lg" /></div>
            <div className="flex gap-2">
              {!isMe && (
                <button className={`btn btn-sm ${likeState.liked_by_me ? "btn-primary" : "btn-secondary"}`} aria-pressed={likeState.liked_by_me} onClick={toggleLike}>
                  <Heart className="h-4 w-4" aria-hidden fill={likeState.liked_by_me ? "currentColor" : "none"} /> {likeState.likes_count}
                </button>
              )}
              {isMe && !editHead && <button className="btn btn-secondary btn-sm" onClick={startHead}><Pencil className="h-4 w-4" aria-hidden /> Edit</button>}
            </div>
          </div>
          {editHead ? (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div><label className="label" htmlFor="h-name">Name</label><input id="h-name" className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></div>
                <div><label className="label" htmlFor="h-loc">Location</label><input id="h-loc" className="input" value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })} /></div>
                <div className="sm:col-span-2"><label className="label" htmlFor="h-head">Headline</label><input id="h-head" className="input" maxLength={120} value={draft.headline} onChange={(e) => setDraft({ ...draft, headline: e.target.value })} /><p className="help">{draft.headline.length}/120</p></div>
                {LINKS.map((l) => (
                  <div key={l.key}><label className="label" htmlFor={`h-${l.key}`}>{l.label} URL</label><input id={`h-${l.key}`} className="input" placeholder="https://" value={draft[l.key]} onChange={(e) => setDraft({ ...draft, [l.key]: e.target.value })} /></div>
                ))}
              </div>
              {linkErr && <p className="error-text">{linkErr}</p>}
              <div className="flex gap-2">
                <button className="btn btn-primary btn-sm" disabled={saving} onClick={saveHead}>{saving ? "Saving…" : "Save"}</button>
                <button className="btn btn-secondary btn-sm" disabled={saving} onClick={() => setEditHead(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold text-slate-900">{p.user.name}</h1>
                <span className="badge capitalize">{role}</span>
              </div>
              {p.headline ? <p className="text-slate-700">{p.headline}</p> : isMe && <p className="muted text-sm">Add a headline so people know what you do.</p>}
              <div className="muted flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                {p.location && <span className="inline-flex items-center gap-1"><MapPin className="h-4 w-4" aria-hidden />{p.location}</span>}
                <span>Member since {formatDate(p.member_since)}</span>
                {hasRating && <span>{p.projects_done} project{p.projects_done === 1 ? "" : "s"} done</span>}
                {!isMe && <span>{likeState.likes_count} like{likeState.likes_count === 1 ? "" : "s"}</span>}
              </div>
              {hasRating && <StarRating value={p.rating} showValue />}
              <div className="flex gap-3 text-slate-600">
                {LINKS.filter((l) => links[l.key]).map((l) => (
                  <a key={l.key} href={links[l.key]} target="_blank" rel="noopener noreferrer" aria-label={l.label} className="hover:text-indigo-600"><LinkIcon k={l.key} /></a>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {(isMe || p.about) && (
        <section className="card space-y-3 p-5" aria-label="About">
          <div className="flex items-center justify-between"><h2 className="section-title">About</h2>
            {isMe && !editAbout && <button className="btn btn-ghost btn-sm" onClick={() => { setAboutDraft(p.about ?? ""); setEditAbout(true); }}><Pencil className="h-4 w-4" aria-hidden /> Edit</button>}
          </div>
          {editAbout ? (
            <div className="space-y-2">
              <label className="sr-only" htmlFor="about">About</label>
              <textarea id="about" className="input min-h-[140px]" value={aboutDraft} onChange={(e) => setAboutDraft(e.target.value)} />
              <p className="help">{aboutDraft.length}/2000</p>
              <div className="flex gap-2">
                <button className="btn btn-primary btn-sm" disabled={saving} onClick={saveAbout}>{saving ? "Saving…" : "Save"}</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setEditAbout(false)}>Cancel</button>
              </div>
            </div>
          ) : p.about ? <p className="whitespace-pre-line text-sm text-slate-700">{p.about}</p> : <p className="muted text-sm">Tell people about yourself.</p>}
        </section>
      )}

      {role !== "sponsor" && (p.skills.length > 0 || canEditSkills) && (
        <section className="card space-y-3 p-5" aria-label="Skills">
          <div className="flex items-center justify-between"><h2 className="section-title">Skills</h2>
            {canEditSkills && <button className="btn btn-ghost btn-sm" onClick={() => setEditSkills(!editSkills)}>{editSkills ? "Done" : "Edit"}</button>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {p.skills.map((s) => (
              <SkillChip key={s} label={skillLabel(s)} variant="selected"
                onRemove={editSkills && (role === "student" || p.skills.length > 1) ? () => { void patch({ remove_skills: [s] }); } : undefined} />
            ))}
            {isMe && (p.pending_skills ?? []).map((s) => (
              <span key={s} className="badge gap-1.5 border border-dashed border-amber-300 bg-amber-50 text-amber-800">
                {skillLabel(s)} · Pending verification
                {editSkills && <button type="button" aria-label={`Remove ${skillLabel(s)}`} onClick={() => { void patch({ remove_skills: [s] }); }}>×</button>}
              </span>
            ))}
            {p.skills.length === 0 && (p.pending_skills ?? []).length === 0 && <p className="muted text-sm">No skills yet.</p>}
          </div>
          {isMe && role === "student" && (p.pending_skills ?? []).length > 0 && (
            <Link href="/student/quiz" className="btn btn-primary btn-sm">Take quiz</Link>
          )}
          {editSkills && (
            <div className="space-y-2">
              <div className="flex gap-2">
                <label className="sr-only" htmlFor="new-skill">Add skill</label>
                <select id="new-skill" className="input" value={skillToAdd} onChange={(e) => setSkillToAdd(e.target.value)}>
                  <option value="">Add skill…</option>
                  {availableSkills.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
                <button className="btn btn-secondary" disabled={!skillToAdd} onClick={async () => { if (await patch({ add_skills: [skillToAdd] })) setSkillToAdd(""); }}>Add</button>
              </div>
              <p className="help">{role === "student" ? "New skills need to pass a quiz before they are verified and used for matching." : "Skills are updated immediately. Keep at least one."}</p>
            </div>
          )}
        </section>
      )}

      {(SECTIONS[role] ?? []).map((cfg) => (
        <DetailSection key={cfg.title} cfg={cfg} details={details} isMe={isMe} onSave={(d) => patch({ details: { ...details, ...d } })} />
      ))}

      <section className="space-y-3" aria-label="Work and projects">
        <h2 className="section-title">Work &amp; projects</h2>
        {p.works.length === 0 ? (
          <div className="card muted p-5 text-sm">{isMe ? "Projects with public files appear here." : "No public projects yet."}</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {p.works.map((w) => (
              <Link key={w.project_id} href={`/explore/${w.project_id}`} className="card card-hover block space-y-2 p-5">
                <div className="flex items-start justify-between gap-3"><h3 className="font-semibold text-slate-900">{w.title}</h3><StatusBadge status={w.status} /></div>
                <p className="muted text-sm capitalize">{w.my_role}{w.skill ? ` · ${skillLabel(w.skill)}` : ""}</p>
                <p className="muted text-xs">{w.public_file_count} public file{w.public_file_count === 1 ? "" : "s"} · since {formatDate(w.started_at)}</p>
              </Link>
            ))}
          </div>
        )}
      </section>

      {isMe && <WalletCard />}
      {isMe && integrity.data && integrity.data.length > 0 && (
        <section className="card space-y-2 border-amber-300 bg-amber-50 p-5" aria-label="My warnings">
          <h2 className="section-title">My warnings</h2>
          <ul className="space-y-2 text-sm text-slate-800">
            {integrity.data.map((i) => <li key={i.id}>{formatDate(i.created_at)}: {i.detail}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
