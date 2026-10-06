"use client";

import { useAuth } from "@/lib/auth";

export default function BlockedNotice() {
  const { logout } = useAuth();
  return (
    <div role="alertdialog" aria-modal="true" aria-labelledby="blocked-title" className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-50 p-6">
      <div className="card max-w-md space-y-4 text-center">
        <h1 id="blocked-title" className="section-title">Your account is blocked</h1>
        <p className="muted">
          Copied work was detected again after an earlier warning, so this submission was not stored and your
          account has been blacklisted. Your researchers and sponsor were notified.
        </p>
        <button type="button" onClick={logout} className="btn btn-primary">Log out</button>
      </div>
    </div>
  );
}
