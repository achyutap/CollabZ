"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, FlaskConical, GraduationCap, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";
import { ApiError } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { toast } from "@/lib/toast";
import type { RegisterPayload, Role } from "@/lib/types";
import { Logo, SKILLS, SkillChip, Spinner } from "@/components/common";

const ROLES: { role: Role; title: string; desc: string; icon: LucideIcon }[] = [
  { role: "sponsor", title: "Sponsor", desc: "Fund a real problem and track its solution.", icon: Wallet },
  { role: "researcher", title: "Researcher", desc: "Lead the work and build a student team.", icon: FlaskConical },
  { role: "student", title: "Student", desc: "Do the work, build skills and earn rewards.", icon: GraduationCap },
];

interface Errors {
  name?: string;
  email?: string;
  password?: string;
  confirm?: string;
  skills?: string;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [role, setRole] = useState<Role | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [skills, setSkills] = useState<string[]>([]);
  const [bio, setBio] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);

  const toggleSkill = (id: string) => setSkills((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!role) return;
    const next: Errors = {};
    if (!name.trim()) next.name = "Name is required";
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = "Enter a valid email address";
    if (password.length < 8) next.password = "Password must be at least 8 characters";
    if (confirm !== password) next.confirm = "Passwords do not match";
    if (role === "researcher" && skills.length < 1) next.skills = "Pick at least one skill";
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    const payload: RegisterPayload = { email: email.trim(), password, name: name.trim(), role };
    if (role !== "sponsor" && skills.length > 0) payload.skills = skills;
    if (role === "researcher" && bio.trim()) payload.bio = bio.trim();
    setSubmitting(true);
    try {
      const u = await register(payload);
      router.replace(homeFor(u));
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) setErrors({ email: "An account with this email already exists" });
        toast.error(err.detail);
      } else {
        toast.error("Something went wrong");
      }
      setSubmitting(false);
    }
  };

  const field = (bad?: string) => clsx("input", bad && "!border-red-400");

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-indigo-50/60 to-slate-50 p-4">
      <div className="w-full max-w-lg space-y-4">
        <div className="text-center">
          <Logo className="text-3xl" />
          <h1 className="mt-2 text-lg font-semibold text-slate-900">Create your account</h1>
          <p className="muted">{role ? "Step 2 of 2: your details" : "Step 1 of 2: choose your role"}</p>
        </div>

        {!role ? (
          <div className="grid gap-3">
            {ROLES.map((r) => {
              const Icon = r.icon;
              return (
                <button key={r.role} type="button" onClick={() => setRole(r.role)} className="card card-hover flex items-center gap-4 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500">
                  <span className="rounded-xl bg-indigo-50 p-3 text-indigo-600">
                    <Icon className="h-6 w-6" aria-hidden />
                  </span>
                  <span>
                    <span className="block font-semibold text-slate-900">{r.title}</span>
                    <span className="block text-sm text-slate-500">{r.desc}</span>
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <form onSubmit={onSubmit} noValidate className="card space-y-4">
            <p className="text-sm text-slate-600">
              Registering as <span className="font-semibold capitalize">{role}</span>{" "}
              <button type="button" onClick={() => setRole(null)} className="text-indigo-600 hover:underline">
                (change)
              </button>
            </p>
            <div>
              <label htmlFor="name" className="label">Name</label>
              <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" aria-invalid={!!errors.name} className={field(errors.name)} />
              {errors.name && <p className="error-text">{errors.name}</p>}
            </div>
            <div>
              <label htmlFor="email" className="label">Email</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" aria-invalid={!!errors.email} className={field(errors.email)} />
              {errors.email && <p className="error-text">{errors.email}</p>}
            </div>
            <div>
              <label htmlFor="password" className="label">Password</label>
              <div className="relative">
                <input id="password" type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" aria-invalid={!!errors.password} className={`${field(errors.password)} pr-10`} />
                <button type="button" onClick={() => setShowPw((v) => !v)} aria-label={showPw ? "Hide password" : "Show password"} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800">
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="error-text">{errors.password}</p>}
            </div>
            <div>
              <label htmlFor="confirm" className="label">Confirm password</label>
              <input id="confirm" type={showPw ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" aria-invalid={!!errors.confirm} className={field(errors.confirm)} />
              {errors.confirm && <p className="error-text">{errors.confirm}</p>}
            </div>

            {role !== "sponsor" && (
              <fieldset>
                <legend className="label">{role === "researcher" ? "Your skills (pick at least one)" : "Your skills (optional)"}</legend>
                <div className="flex flex-wrap gap-2">
                  {SKILLS.map((s) => (
                    <SkillChip key={s.id} label={s.label} variant={skills.includes(s.id) ? "selected" : "default"} onClick={() => toggleSkill(s.id)} />
                  ))}
                </div>
                {role === "student" && <p className="help">You&apos;ll take a short quiz to verify these skills.</p>}
                {errors.skills && <p className="error-text">{errors.skills}</p>}
              </fieldset>
            )}

            {role === "researcher" && (
              <div>
                <label htmlFor="bio" className="label">Bio (optional)</label>
                <textarea id="bio" rows={3} value={bio} onChange={(e) => setBio(e.target.value)} className="input" />
              </div>
            )}

            <button type="submit" disabled={submitting} className="btn btn-primary w-full">
              {submitting && <Spinner className="h-4 w-4 text-white" />}
              Create account
            </button>
          </form>
        )}
        <p className="text-center text-sm text-slate-500">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-indigo-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
