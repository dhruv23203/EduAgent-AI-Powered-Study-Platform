"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  CalendarClock,
  CheckCircle2,
  Clock3,
  GraduationCap,
  Layers3,
  Loader2,
  LogOut,
  Plus,
  Trash2
} from "lucide-react";
import { currentUserFromStorage, deleteStudyPlan, getStudyPlans, logout, StudyPlanStatus, StudyPlanSummary } from "@/lib/api";

type PlanTab = "current" | "existing" | "completed";

const tabCopy: Record<PlanTab, { label: string; title: string; empty: string }> = {
  current: { label: "Current", title: "Current plan", empty: "No running plan yet. Create a plan with today inside its schedule." },
  existing: { label: "Existing", title: "Active and upcoming plans", empty: "No active or upcoming plans. Add a new study plan to start." },
  completed: { label: "Completed", title: "Completed plans", empty: "Completed plans will appear here after their exam date passes." }
};

export default function PlansPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<StudyPlanSummary[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<PlanTab>("existing");

  useEffect(() => {
    const user = currentUserFromStorage();
    if (!user) {
      router.replace("/login?mode=login");
      return;
    }
    setName(user.name);
    getStudyPlans(user.id).then((rows) => {
      setPlans(rows);
      setActiveTab(rows.some((plan) => plan.status === "running") ? "current" : "existing");
    }).finally(() => setLoading(false));
  }, [router]);

  const groups = useMemo(() => {
    const current = plans.filter((plan) => plan.status === "running");
    const existing = plans.filter((plan) => plan.status !== "completed");
    const completed = plans.filter((plan) => plan.status === "completed");
    return { current, existing, completed };
  }, [plans]);

  const visiblePlans = groups[activeTab];
  const stats = useMemo(() => ({
    all: plans.length,
    active: groups.existing.length,
    completed: groups.completed.length,
    hours: plans.reduce((total, plan) => total + plan.total_hours, 0)
  }), [groups, plans]);

  function signOut() {
    logout();
    router.replace("/");
  }

  function openPlan(planId: number) {
    localStorage.setItem("eduagent_selected_plan_id", String(planId));
    router.push(`/dashboard?planId=${planId}`);
  }

  async function removePlan(plan: StudyPlanSummary) {
    const user = currentUserFromStorage();
    if (!user) return;
    const ok = window.confirm(`Delete "${plan.title}" and its linked quiz/task data?`);
    if (!ok) return;
    setDeletingId(plan.id);
    try {
      await deleteStudyPlan(user.id, plan.id);
      setPlans((current) => current.filter((item) => item.id !== plan.id));
      if (localStorage.getItem("eduagent_selected_plan_id") === String(plan.id)) {
        localStorage.removeItem("eduagent_selected_plan_id");
      }
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-ink text-white">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1800&q=80')] bg-cover bg-center opacity-40" />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(9,16,24,.97)_0%,rgba(9,16,24,.91)_48%,rgba(31,122,95,.58)_100%)]" />
      <div className="hero-grid absolute inset-0" />

      <section className="relative mx-auto max-w-7xl px-5 py-7 sm:px-6 lg:py-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Link href="/" className="group flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-lg bg-fern shadow-panel transition group-hover:-translate-y-0.5">
              <GraduationCap />
            </span>
            <span>
              <b className="block text-2xl">EduAgent</b>
              <span className="text-sm font-bold text-white/62">Plan library</span>
            </span>
          </Link>
          <div className="flex flex-wrap gap-3">
            <span className="rounded-lg border border-white/15 bg-white/10 px-4 py-3 text-sm font-bold shadow-soft backdrop-blur-md">Signed in as {name}</span>
            <Link href="/setup?new=1" className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-4 py-3 text-sm font-black text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-emerald-700">
              <Plus className="h-4 w-4" /> Add new plan
            </Link>
            <button onClick={signOut} className="focus-ring inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-4 py-3 text-sm font-bold transition hover:bg-white/16">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </header>

        <div className="mt-12 grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
          <div>
            <p className="inline-flex rounded-full border border-white/16 bg-white/10 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-emerald-100 backdrop-blur-md">Current, existing, completed</p>
            <h1 className="mt-5 max-w-4xl text-5xl font-black leading-tight sm:text-6xl">Choose the plan you want to work on.</h1>
            <p className="mt-5 max-w-3xl text-xl leading-8 text-white/76">
              Open a running plan, review active plans, or archive completed work. Every plan stays saved to your account.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <StatCard icon={Layers3} label="Saved" value={stats.all} />
            <StatCard icon={Clock3} label="Active" value={stats.active} />
            <StatCard icon={CheckCircle2} label="Complete" value={stats.completed} />
            <StatCard icon={CalendarClock} label="Hours" value={Math.round(stats.hours)} />
          </div>
        </div>

        <div className="mt-8 rounded-lg border border-white/16 bg-white/10 p-2 shadow-panel backdrop-blur-md">
          <div className="grid gap-2 md:grid-cols-3">
            {(Object.keys(tabCopy) as PlanTab[]).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`focus-ring rounded-md px-4 py-4 text-left transition ${activeTab === tab ? "bg-white text-ink shadow-soft" : "text-white/68 hover:bg-white/10 hover:text-white"}`}
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="font-black">{tabCopy[tab].label}</span>
                  <span className={`rounded-full px-2 py-1 text-xs font-black ${activeTab === tab ? "bg-fern text-white" : "bg-white/10 text-white/75"}`}>{groups[tab].length}</span>
                </span>
                <span className="mt-1 block text-sm font-semibold opacity-70">{tab === "current" ? "Running today" : tab === "existing" ? "Not completed" : "Exam date passed"}</span>
              </button>
            ))}
          </div>
        </div>

        <section className="mt-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="section-kicker">{tabCopy[activeTab].label}</p>
              <h2 className="mt-1 text-3xl font-black">{tabCopy[activeTab].title}</h2>
            </div>
            <Link href="/setup?new=1" className="focus-ring inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-4 py-3 font-black text-white transition hover:bg-white/16">
              <Plus className="h-4 w-4" /> New plan
            </Link>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            {loading ? <div className="rounded-lg border border-white/15 bg-white/10 p-6 font-bold"><Loader2 className="mr-2 inline h-5 w-5 animate-spin text-emerald-200" /> Loading plans...</div> : null}
            {!loading && !visiblePlans.length ? (
              <EmptyState title={tabCopy[activeTab].empty} />
            ) : null}
            {visiblePlans.map((plan) => (
              <PlanCard key={plan.id} plan={plan} deleting={deletingId === plan.id} onOpen={() => openPlan(plan.id)} onDelete={() => removePlan(plan)} />
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function StatCard({ icon: Icon, label, value }: { icon: typeof Layers3; label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-white/16 bg-white/10 p-4 shadow-soft backdrop-blur-md">
      <Icon className="h-5 w-5 text-amber" />
      <p className="mt-3 text-xs font-black uppercase tracking-[0.16em] text-white/45">{label}</p>
      <p className="mt-1 text-2xl font-black">{value}</p>
    </div>
  );
}

function EmptyState({ title }: { title: string }) {
  return (
    <div className="lg:col-span-3 rounded-lg border border-dashed border-white/20 bg-white/10 p-10 text-center shadow-soft backdrop-blur-md">
      <BookOpenCheck className="mx-auto h-12 w-12 text-amber" />
      <h3 className="mt-4 text-2xl font-black">Nothing here yet</h3>
      <p className="mx-auto mt-2 max-w-xl text-white/68">{title}</p>
      <Link href="/setup?new=1" className="focus-ring mt-6 inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-black text-white transition hover:bg-emerald-700">
        Add new plan <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function PlanCard({ plan, deleting, onOpen, onDelete }: { plan: StudyPlanSummary; deleting: boolean; onOpen: () => void; onDelete: () => void }) {
  const statusStyles: Record<StudyPlanStatus, string> = {
    running: "bg-fern text-white",
    upcoming: "bg-amber text-ink",
    completed: "bg-white text-ink"
  };
  return (
    <article className="group rounded-lg border border-white/16 bg-white/10 p-5 shadow-panel backdrop-blur-md transition hover:-translate-y-1 hover:border-amber/40 hover:bg-white/15">
      <div className="flex items-start justify-between gap-3">
        <span className={`rounded-md px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${statusStyles[plan.status]}`}>{plan.status}</span>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="focus-ring grid h-9 w-9 place-items-center rounded-md border border-white/12 bg-white/10 text-white/70 transition hover:border-coral/50 hover:bg-coral/20 hover:text-white disabled:opacity-50"
          aria-label={`Delete ${plan.title}`}
        >
          {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
        </button>
      </div>
      <h3 className="mt-4 text-2xl font-black text-white">{plan.title}</h3>
      <p className="mt-2 text-sm font-semibold text-white/62">{plan.total_days} days | {plan.total_sessions} sessions | {Math.round(plan.total_hours)}h</p>
      <div className="mt-5 grid grid-cols-3 gap-2">
        <MiniStat label="Topics" value={plan.topic_count} />
        <MiniStat label="Daily" value={`${plan.daily_hours}h`} />
        <MiniStat label="Start" value={plan.start_date?.slice(5) || "--"} />
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {plan.primary_topics.slice(0, 4).map((topic) => <span key={topic} className="rounded-md bg-white/10 px-2 py-1 text-xs font-bold text-white/75">{topic}</span>)}
      </div>
      <button onClick={onOpen} className="focus-ring mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-ink transition hover:-translate-y-0.5 hover:bg-amber">
        Open dashboard <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
      </button>
    </article>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/10 p-2">
      <p className="text-[10px] font-black uppercase tracking-[0.14em] text-white/42">{label}</p>
      <p className="mt-1 font-black text-white">{value}</p>
    </div>
  );
}
