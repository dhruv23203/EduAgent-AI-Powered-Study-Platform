"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BarChart3, BookOpenCheck, BriefcaseBusiness, GraduationCap, LayoutDashboard, LogOut, MessageSquareText, Moon, PenSquare, Plus, Repeat2, Sun } from "lucide-react";
import { currentUserFromStorage, getMe, getProgress, getUsage, logout, RewardSummary, UsageResponse, UserProfile } from "@/lib/api";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/quiz", label: "Quiz", icon: PenSquare },
  { href: "/revision", label: "Revision", icon: Repeat2 },
  { href: "/progress", label: "Progress", icon: BarChart3 },
  { href: "/chat", label: "Chat", icon: MessageSquareText },
  { href: "/career", label: "Career", icon: BriefcaseBusiness }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [planRewards, setPlanRewards] = useState<RewardSummary | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("eduagent_theme") === "dark";
    setDark(saved);
    document.documentElement.classList.toggle("dark", saved);
    const storedUser = currentUserFromStorage();
    const selectedPlanId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    setUser(storedUser);
    getMe().then(setUser).catch(() => {});
    if (storedUser) {
      getProgress(storedUser.id, selectedPlanId).then((progress) => setPlanRewards(progress.rewards)).catch(() => {});
    }
    getUsage().then(setUsage).catch(() => {});
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("eduagent_theme", next ? "dark" : "light");
    document.documentElement.classList.toggle("dark", next);
  }

  function signOut() {
    logout();
    router.replace("/");
  }

  return (
    <div className="min-h-screen bg-[#f4f7f5] text-ink dark:bg-[#0f1720] dark:text-white">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 flex-col overflow-y-auto border-r border-white/10 bg-ink px-5 py-5 text-white lg:flex">
        <Link href="/plans" className="focus-ring flex items-center gap-3 rounded-lg px-2 py-2">
          <span className="grid h-11 w-11 place-items-center rounded-lg bg-fern text-white shadow-soft"><GraduationCap className="h-5 w-5" /></span>
          <span><span className="block text-xl font-black">EduAgent</span><span className="text-sm text-white/60">Study cockpit</span></span>
        </Link>
        <nav className="mt-10 grid gap-2">
          {items.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            const href = item.href === "/dashboard" ? `/dashboard?planId=${typeof window !== "undefined" ? localStorage.getItem("eduagent_selected_plan_id") || "" : ""}` : item.href;
            return (
              <Link key={item.href} href={href} className={`focus-ring flex items-center gap-3 rounded-lg px-4 py-3 font-bold ${active ? "bg-white text-ink shadow-soft" : "text-white/60 hover:bg-white/10 hover:text-white"}`}>
                <Icon className="h-5 w-5" /> {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto grid gap-4">
          <div className="rounded-lg border border-white/15 bg-white/10 p-4">
            <div className="flex items-center justify-between">
              <p className="font-black">{user?.name || "Student"}</p>
              <button onClick={toggleTheme} className="focus-ring rounded-md p-2 text-white/70 hover:bg-white/10">{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="rounded-md bg-white/10 p-3 text-sm"><span className="block text-white/60">Plan coins</span><b className="text-xl">{planRewards?.coins ?? user?.coins ?? 0}</b></div>
              <div className="rounded-md bg-white/10 p-3 text-sm"><span className="block text-white/60">Plan badges</span><b className="text-xl">{planRewards?.badges.length ?? user?.badges.length ?? 0}</b></div>
            </div>
          </div>
          <div className="rounded-lg border border-white/15 bg-white/10 p-4">
            <p className="font-black">AI budget</p>
            <p className="mt-2 text-sm text-white/70">{usage ? `${usage.provider || "AI"} ${usage.requests_used}/${usage.daily_limit} requests used today.` : "Budget loading..."}</p>
            <button onClick={signOut} className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md text-sm font-bold text-white/70 hover:text-white"><LogOut className="h-4 w-4" /> Sign out</button>
          </div>
        </div>
      </aside>
      <header className="sticky top-0 z-10 border-b border-ink/10 bg-white/95 px-4 py-3 backdrop-blur dark:border-white/10 dark:bg-[#151f2a]/95 lg:hidden">
        <div className="flex items-center justify-between">
          <Link href="/plans" className="font-black">EduAgent</Link>
          <div className="flex gap-2">
            <Link href="/setup?new=1" className="rounded-md bg-fern p-2 text-white"><Plus className="h-4 w-4" /></Link>
            <button onClick={toggleTheme} className="rounded-md bg-mist p-2 dark:bg-white/10">{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
          </div>
        </div>
      </header>
      <main className="px-4 py-6 lg:ml-72 lg:px-8">{children}</main>
    </div>
  );
}
