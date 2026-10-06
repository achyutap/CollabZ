"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Ban } from "lucide-react";
import { ApiError, BLACKLIST_KEY } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { toast } from "@/lib/toast";
import { Logo, Spinner } from "@/components/common";

const DEMOS = [
  { label: "Sponsor", email: "sponsor1@demo.com" },
  { label: "Researcher", email: "researcher1@demo.com" },
  { label: "Student", email: "student1@demo.com" },
];

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({});
  const [blocked, setBlocked] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    try {
      const msg = window.sessionStorage.getItem(BLACKLIST_KEY);
      if (msg) {
        setBlocked(msg);
        window.sessionStorage.removeItem(BLACKLIST_KEY);
      }
    } catch {
      /* storage unavailable */
    }
  }, []);

  useEffect(() => {
    if (!loading && user && !submitting) router.replace(homeFor(user));
  }, [loading, user, submitting, router]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: typeof errors = {};
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = "Enter a valid email address";
    if (!password) next.password = "Password is required";
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    setBlocked(null);
    setSubmitting(true);
    try {
      const u = await login(email.trim(), password);
      router.replace(homeFor(u));
    } catch (err) {
      if (err instanceof ApiError && err.code === "BLACKLISTED") {
        setBlocked(err.detail || "This account has been blacklisted and can no longer be used.");
        setErrors({});
      } else {
        const detail = err instanceof ApiError ? err.detail : "Something went wrong";
        setErrors({ form: detail });
        toast.error(detail);
      }
      setSubmitting(false);
    }
  };

  const fill = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("demo1234");
    setErrors({});
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-indigo-50/60 to-slate-50 p-4">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center">
          <Logo className="text-3xl" />
          <p className="muted mt-2">Sign in to your account</p>
        </div>

        {blocked && (
          <div role="alert" className="flex gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800">
            <Ban className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
            <div>
              <p className="font-semibold">Account blacklisted</p>
              <p className="mt-1 text-sm">{blocked}</p>
            </div>
          </div>
        )}

        <form onSubmit={onSubmit} noValidate className="card space-y-4">
          {errors.form && (
            <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
              {errors.form}
            </p>
          )}
          <div>
            <label htmlFor="email" className="label">Email</label>
            <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!errors.email} className={`input ${errors.email ? "!border-red-400" : ""}`} />
            {errors.email && <p className="error-text">{errors.email}</p>}
          </div>
          <div>
            <label htmlFor="password" className="label">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} className={`input ${errors.password ? "!border-red-400" : ""}`} />
            {errors.password && <p className="error-text">{errors.password}</p>}
          </div>
          <button type="submit" disabled={submitting} className="btn btn-primary w-full">
            {submitting && <Spinner className="h-4 w-4 text-white" />}
            Sign in
          </button>
          <p className="text-center text-sm text-slate-500">
            New to CollabZ?{" "}
            <Link href="/register" className="font-medium text-indigo-600 hover:underline">
              Create an account
            </Link>
          </p>
        </form>

        <div className="card !p-4">
          <h2 className="text-sm font-semibold text-slate-800">Demo accounts</h2>
          <p className="help mb-3">Password: demo1234</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {DEMOS.map((d) => (
              <button key={d.email} type="button" onClick={() => fill(d.email)} className="rounded-xl border border-slate-200 px-3 py-2 text-left text-xs transition hover:border-indigo-300 hover:bg-indigo-50/40">
                <span className="block font-medium text-slate-800">{d.label}</span>
                <span className="block truncate text-slate-500">{d.email}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
