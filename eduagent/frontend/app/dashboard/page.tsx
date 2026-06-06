"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarClock, CheckCircle2, ClipboardList, Download, Loader2, Plus, RotateCcw, Sparkles, Target, type LucideIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ProgressRing } from "@/components/ProgressRing";
import { StudyPlanView } from "@/components/StudyPlanView";
import { API_URL, completeTask, currentUserFromStorage, DailyTaskStatus, getDailyTask, getProgress, getStudyPlan, ProgressResponse, StudyDay } from "@/lib/api";

const quotes = ["Small wins compound into exam confidence.", "Do the next honest block. Momentum follows.", "Mistakes are coordinates, not losses.", "The streak is built one focused session at a time."];

function progressCacheKey(studentId: string) { return `eduagent_progress_${studentId}`; }
function readCachedProgress(studentId: string): ProgressResponse | null {
  const raw = typeof window !== "undefined" ? localStorage.getItem(progressCacheKey(studentId)) : null;
  if (!raw) return null;
  try { return JSON.parse(raw) as ProgressResponse; } catch { return null; }
}
function writeCachedProgress(studentId: string, data: ProgressResponse) { localStorage.setItem(progressCacheKey(studentId), JSON.stringify(data)); }

export default function DashboardPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<StudyDay[]>([]);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [dailyTask, setDailyTask] = useState<DailyTaskStatus | null>(null);
  const [studentId, setStudentId] = useState("");
  const [examDate, setExamDate] = useState("");
  const [activePlanId, setActivePlanId] = useState<number | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(true);
  const [quote, setQuote] = useState(quotes[0]);

  useEffect(() => {
    const user = currentUserFromStorage();
    if (!user) { router.replace("/login?mode=login"); return; }
    const params = new URLSearchParams(window.location.search);
    const planId = Number(params.get("planId") || localStorage.getItem("eduagent_selected_plan_id") || "");
    if (!planId) { router.replace("/plans"); return; }
    setStudentId(user.id);
    setActivePlanId(planId);
    setQuote(quotes[Math.floor(Math.random() * quotes.length)]);
    const cached = readCachedProgress(user.id);
    if (cached) setProgress(cached);
    getStudyPlan(user.id, planId).then((detail) => {
      setPlan(detail.study_plan);
      setExamDate(detail.study_plan[detail.study_plan.length - 1]?.date || "");
      localStorage.setItem("eduagent_selected_plan_id", String(planId));
    }).finally(() => setLoadingPlan(false));
    getProgress(user.id).then((data) => { setProgress(data); writeCachedProgress(user.id, data); }).finally(() => setLoadingProgress(false));
    getDailyTask(user.id, new Date().toISOString().slice(0, 10), planId).then(setDailyTask).catch(() => setDailyTask(null));
  }, [router]);

  async function markTask(type: "concepts" | "practice") {
    if (!dailyTask || !studentId) return;
    const updated = await completeTask(studentId, dailyTask.date, type, dailyTask.topic, activePlanId);
    setDailyTask(updated);
    setLoadingProgress(true);
    const latest = await getProgress(studentId).catch(() => null);
    if (latest) { setProgress(latest); writeCachedProgress(studentId, latest); }
    setLoadingProgress(false);
  }

  const coverage = useMemo(() => {
    if (!plan.length || !progress?.heatmap?.length) return 0;
    const dates = new Set(plan.map((day) => day.date));
    const done = progress.heatmap.filter((day) => dates.has(day.date) && (day.count >= 5 || day.recovered)).length;
    return Math.min(100, Math.round((done / plan.length) * 100));
  }, [plan, progress]);
  const daysRemaining = examDate ? Math.max(0, Math.ceil((new Date(examDate).getTime() - Date.now()) / 86400000)) : 0;
  const today = new Date().toISOString().slice(0, 10);
  const todaysPlan = plan.find((day) => day.date === today) ?? plan[0];
  const todaysHours = todaysPlan?.sessions.reduce((sum, session) => sum + session.hours, 0) ?? 0;

  if (loadingPlan) return <AppShell><div className="grid min-h-[65vh] place-items-center"><div className="panel flex items-center gap-4 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Opening selected plan dashboard...</div></div></AppShell>;

  return (
    <AppShell>
      <section className="overflow-hidden rounded-lg bg-ink text-white shadow-panel">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_320px] lg:p-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/60">Plan dashboard</p>
            <h1 className="mt-3 text-4xl font-black">Today&apos;s study lane</h1>
            <p className="mt-3 text-white/70">{todaysPlan ? `${todaysPlan.sessions.length} focused session scheduled today.` : "Choose a plan to fill your daily workspace."}</p>
            <blockquote className="mt-5 rounded-lg border border-white/10 bg-white/10 p-5"><div className="flex gap-3"><Sparkles className="h-8 w-8 text-amber" /><p className="text-2xl font-black">{quote}</p></div></blockquote>
            <div className="mt-6 flex flex-wrap gap-3"><Metric label="Today" value={`${todaysHours}h`} /><Metric label="Plan days" value={plan.length} /><Metric label="Exam" value={`${daysRemaining}d`} /></div>
          </div>
          <div className="flex flex-col justify-end gap-3">
            <Link href={`/quiz?fresh=${Date.now()}`} className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-emerald-700">Start Today&apos;s Quiz <ArrowRight className="h-5 w-5" /></Link>
            <Link href="/plans" className="focus-ring inline-flex items-center justify-center rounded-lg border border-white/15 bg-white/10 px-5 py-3 font-bold text-white hover:bg-white/15">Change plan</Link>
            <Link href="/setup?new=1" className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/10 px-5 py-3 font-bold text-white hover:bg-white/15"><Plus className="h-4 w-4" /> Add new plan</Link>
          </div>
        </div>
      </section>
      {studentId ? <section className="mt-6 flex flex-wrap gap-3"><a href={`${API_URL}/api/export/studyplan/${studentId}`} className="panel inline-flex items-center gap-2 px-4 py-3 text-sm font-bold"><Download className="h-4 w-4 text-fern" /> Study plan TXT</a><a href={`${API_URL}/api/export/flashcards/${studentId}`} className="panel inline-flex items-center gap-2 px-4 py-3 text-sm font-bold"><Download className="h-4 w-4 text-fern" /> Flashcards CSV</a></section> : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_320px]">
        <StudyPlanView plan={plan} compact />
        <section className="panel p-5">
          <ProgressRing value={coverage} label="Plan done" />
          <div className="mt-6 grid gap-3">
            <Stat icon={ClipboardList} label="Questions" value={progress?.total_questions_attempted ?? 0} loading={loadingProgress && !progress} />
            <Stat icon={Target} label="Accuracy" value={`${progress?.overall_accuracy ?? 0}%`} loading={loadingProgress && !progress} />
            <Stat icon={CheckCircle2} label="Streak" value={`${progress?.streak_days ?? 0} days`} loading={loadingProgress && !progress} />
            <Stat icon={CalendarClock} label="Exam" value={`${daysRemaining} days`} />
          </div>
        </section>
      </div>
      {dailyTask ? <section className="panel mt-6 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">Today&apos;s Completion</p><h2 className="text-xl font-black">{dailyTask.topic}</h2><p className="text-sm text-ink/60 dark:text-white/60">{dailyTask.subtopic}</p></div><span className={`rounded-md px-3 py-2 text-sm font-black ${dailyTask.day_completed ? "bg-fern text-white" : "bg-amber/20 text-ink dark:text-amber"}`}>{dailyTask.day_completed ? "Streak day complete" : "Complete all 3 missions"}</span></div><div className="mt-4 grid gap-3 md:grid-cols-3"><Mission label="Concepts" done={dailyTask.concepts_completed} onClick={() => markTask("concepts")} /><Mission label="Practice problems" done={dailyTask.practice_completed} onClick={() => markTask("practice")} /><Mission label={`3 quizzes (${Math.min(dailyTask.quiz_count, 3)}/3)`} done={dailyTask.quiz_completed} href="/quiz" /></div></section> : null}
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-lg border border-white/10 bg-white/10 px-4 py-3"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/50">{label}</p><p className="mt-1 text-2xl font-black">{value}</p></div>; }
function Stat({ icon: Icon, label, value, loading = false }: { icon: LucideIcon; label: string; value: string | number; loading?: boolean }) { return <div className="flex items-center justify-between rounded-lg border border-ink/10 bg-[#f8faf9] px-3 py-3 dark:border-white/10 dark:bg-white/10"><span className="flex items-center gap-2 text-sm font-medium text-ink/60 dark:text-white/60"><Icon className="h-4 w-4 text-fern" />{label}</span><span className="font-bold">{loading ? <Loader2 className="h-4 w-4 animate-spin text-fern" /> : value}</span></div>; }
function Mission({ label, done, onClick, href }: { label: string; done: boolean; onClick?: () => void; href?: string }) { const className = `focus-ring flex min-h-[76px] items-center justify-between rounded-lg border px-4 py-3 text-left font-bold transition ${done ? "border-fern bg-fern/10 text-fern dark:text-emerald-200" : "border-ink/10 bg-[#f8faf9] text-ink hover:border-fern dark:border-white/10 dark:bg-white/10 dark:text-white"}`; const content = <><span>{label}{onClick && done ? <span className="mt-1 block text-xs opacity-70">Click again to undo</span> : null}</span>{onClick && done ? <RotateCcw className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}</>; return href ? <Link href={href} className={className}>{content}</Link> : <button type="button" onClick={onClick} className={className}>{content}</button>; }
