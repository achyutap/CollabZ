"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardCheck, Compass, Folder, Inbox, Lightbulb, LogOut, Menu, User, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "@/lib/auth";
import { CountsProvider, useCounts } from "@/lib/counts";
import type { CountsOut, Role, UserOut } from "@/lib/types";
import { CountBadge, Logo, Spinner, UserAvatar } from "@/components/common";
import { NotificationBell } from "@/features/notifications/NotificationBell";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  badge: number;
}

function navFor(user: UserOut, counts: CountsOut | undefined): NavItem[] {
  const requests = counts?.requests ?? 0;
  const approvals = counts?.approvals ?? 0;
  const explore: NavItem = { href: "/explore", label: "Explore", icon: Compass, badge: 0 };
  const profile: NavItem = { href: "/profile", label: "Profile", icon: User, badge: 0 };
  switch (user.role) {
    case "sponsor":
      return [
        { href: "/sponsor/problems", label: "Problems", icon: Lightbulb, badge: 0 },
        { href: "/sponsor/projects", label: "Projects", icon: Folder, badge: 0 },
        explore,
        profile,
      ];
    case "researcher":
      return [
        { href: "/researcher/requests", label: "Requests", icon: Inbox, badge: requests },
        { href: "/researcher/projects", label: "Projects", icon: Folder, badge: approvals },
        explore,
        profile,
      ];
    case "student": {
      const pending = user.pending_quiz_skills ?? [];
      const items: NavItem[] = [];
      if (pending.length > 0) items.push({ href: "/student/quiz", label: "Quiz", icon: ClipboardCheck, badge: pending.length });
      items.push(
        { href: "/student/requests", label: "Requests", icon: Inbox, badge: requests },
        { href: "/student/projects", label: "Projects", icon: Folder, badge: 0 },
        explore,
        profile,
      );
      return items;
    }
  }
}

const ROLE_STYLE: Record<Role, string> = {
  sponsor: "bg-amber-50 text-amber-700 ring-amber-200",
  researcher: "bg-violet-50 text-violet-700 ring-violet-200",
  student: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

function Shell({ user, children }: { user: UserOut; children: ReactNode }) {
  const { logout } = useAuth();
  const { counts } = useCounts();
  const router = useRouter();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  const links = navFor(user, counts);

  const nav = (
    <nav aria-label="Main" className="flex flex-col gap-1 p-3">
      {links.map((l) => {
        const active = pathname === l.href || pathname.startsWith(l.href + "/");
        const Icon = l.icon;
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={clsx("flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition", active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100")}
          >
            <Icon className="h-4 w-4" aria-hidden />
            <span className="flex-1">{l.label}</span>
            <CountBadge count={l.badge} />
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen lg:pl-60">
      {drawerOpen && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setDrawerOpen(false)} aria-hidden />}
      <aside className={clsx("fixed inset-y-0 left-0 z-40 w-60 border-r border-slate-200 bg-white transition-transform lg:translate-x-0", drawerOpen ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex h-14 items-center justify-between border-b border-slate-200 px-4">
          <Logo />
          <button type="button" aria-label="Close menu" className="btn btn-ghost !p-1.5 lg:hidden" onClick={() => setDrawerOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>
        {nav}
      </aside>

      <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/90 px-4 backdrop-blur">
        <button type="button" aria-label="Open menu" className="btn btn-ghost !p-1.5 lg:hidden" onClick={() => setDrawerOpen(true)}>
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex-1" />
        <NotificationBell />
        <UserAvatar name={user.name} size="sm" />
        <span className="hidden max-w-[10rem] truncate text-sm font-medium text-slate-800 sm:inline">{user.name}</span>
        <span className={clsx("badge capitalize", ROLE_STYLE[user.role])}>{user.role}</span>
        <button
          type="button"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
          className="btn btn-secondary btn-sm"
        >
          <LogOut className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">Logout</span>
          <span className="sr-only sm:hidden">Logout</span>
        </button>
      </header>

      <main>{children}</main>
    </div>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <CountsProvider>
      <Shell user={user}>{children}</Shell>
    </CountsProvider>
  );
}
