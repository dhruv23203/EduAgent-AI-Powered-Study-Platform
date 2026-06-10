"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  Brain,
  CalendarClock,
  CheckCircle2,
  Circle,
  ClipboardList,
  Download,
  ExternalLink,
  Flame,
  Loader2,
  MessageSquareText,
  PenSquare,
  PlayCircle,
  Plus,
  Repeat2,
  RotateCcw,
  Sparkles,
  Target,
  type LucideIcon
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ProgressRing } from "@/components/ProgressRing";
import {
  API_URL,
  completeTask,
  currentUserFromStorage,
  DailyTaskStatus,
  getDailyTask,
  getProgress,
  getRevision,
  getRevisionQuizHistory,
  getStudyPlan,
  ProgressResponse,
  RevisionQuizHistoryItem,
  RevisionResponse,
  StudyDay,
  StudyResource,
  StudySession
} from "@/lib/api";

const quotes = [
  "Small wins compound into exam confidence.",
  "Do the next honest block. Momentum follows.",
  "Mistakes are coordinates, not losses.",
  "The streak is built one focused session at a time."
];

function progressCacheKey(studentId: string, planId?: number | null) {
  return `eduagent_progress_${studentId}_${planId || "all"}`;
}

function readCachedProgress(studentId: string, planId?: number | null): ProgressResponse | null {
  const raw = typeof window !== "undefined" ? localStorage.getItem(progressCacheKey(studentId, planId)) : null;
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ProgressResponse;
  } catch {
    return null;
  }
}

function writeCachedProgress(studentId: string, planId: number | null | undefined, data: ProgressResponse) {
  localStorage.setItem(progressCacheKey(studentId, planId), JSON.stringify(data));
}

export default function DashboardPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<StudyDay[]>([]);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [revision, setRevision] = useState<RevisionResponse | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<RevisionQuizHistoryItem[]>([]);
  const [dailyTask, setDailyTask] = useState<DailyTaskStatus | null>(null);
  const [studentId, setStudentId] = useState("");
  const [examDate, setExamDate] = useState("");
  const [activePlanId, setActivePlanId] = useState<number | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(true);
  const [loadingRevision, setLoadingRevision] = useState(true);
  const [quote, setQuote] = useState(quotes[0]);

  useEffect(() => {
    const user = currentUserFromStorage();
    if (!user) {
      router.replace("/login?mode=login");
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const planId = Number(params.get("planId") || localStorage.getItem("eduagent_selected_plan_id") || "");
    if (!planId) {
      router.replace("/plans");
      return;
    }
    setStudentId(user.id);
    setActivePlanId(planId);
    setQuote(quotes[Math.floor(Math.random() * quotes.length)]);
    const cached = readCachedProgress(user.id, planId);
    if (cached) setProgress(cached);
    getStudyPlan(user.id, planId)
      .then((detail) => {
        setPlan(detail.study_plan);
        setExamDate(detail.study_plan[detail.study_plan.length - 1]?.date || "");
        localStorage.setItem("eduagent_selected_plan_id", String(planId));
      })
      .finally(() => setLoadingPlan(false));
    getProgress(user.id, planId)
      .then((data) => {
        setProgress(data);
        writeCachedProgress(user.id, planId, data);
      })
      .finally(() => setLoadingProgress(false));
    getDailyTask(user.id, todayIso(), planId)
      .then(setDailyTask)
      .catch(() => setDailyTask(null));
    getRevision(user.id, planId)
      .then(setRevision)
      .catch(() => setRevision(null))
      .finally(() => setLoadingRevision(false));
    getRevisionQuizHistory(user.id, planId)
      .then(setRevisionHistory)
      .catch(() => setRevisionHistory([]));
  }, [router]);

  async function markTask(type: "concepts" | "practice") {
    if (!dailyTask || !studentId) return;
    const updated = await completeTask(studentId, dailyTask.date, type, dailyTask.topic, activePlanId);
    setDailyTask(updated);
    setLoadingProgress(true);
    const latest = await getProgress(studentId, activePlanId).catch(() => null);
    if (latest) {
      setProgress(latest);
      writeCachedProgress(studentId, activePlanId, latest);
    }
    setLoadingProgress(false);
  }

  const today = todayIso();
  const todaysPlan = plan.find((day) => day.date === today) ?? plan[0];
  const todaysSession = todaysPlan?.sessions[0];
  const resources = dailyTask?.resources?.length ? dailyTask.resources : todaysSession?.resources ?? [];
  const topic = dailyTask ? dailyTask.topic : todaysSession?.topic || "Today's topic";
  const subtopic = dailyTask ? dailyTask.subtopic || dailyTask.topic : todaysSession?.subtopic || topic;
  const focusPoints = !dailyTask && todaysSession?.focus_points?.length ? todaysSession.focus_points : [`Master the key concept behind ${subtopic}.`, `Solve important practice problems from ${topic}.`, "Finish 3 quizzes and review every wrong answer."];
  const conceptLinks = resources.filter((item) => item.type !== "Video" && item.type !== "Practice");
  const videoLinks = resources.filter((item) => item.type === "Video");
  const practiceLinks = resources.filter((item) => item.type === "Practice");
  const completionUnits = (dailyTask?.concepts_completed ? 1 : 0) + (dailyTask?.practice_completed ? 1 : 0) + Math.min(dailyTask?.quiz_count ?? 0, 3);
  const completionPercent = Math.round((completionUnits / 5) * 100);

  const coverage = useMemo(() => {
    if (!plan.length || !progress?.heatmap?.length) return 0;
    const dates = new Set(plan.map((day) => day.date));
    const done = progress.heatmap.filter((day) => dates.has(day.date) && (day.count >= 5 || day.recovered)).length;
    return Math.min(100, Math.round((done / plan.length) * 100));
  }, [plan, progress]);
  const daysRemaining = examDate ? Math.max(0, Math.ceil((new Date(examDate).getTime() - Date.now()) / 86400000)) : 0;
  const todaysHours = todaysPlan?.sessions.reduce((sum, session) => sum + session.hours, 0) ?? 0;
  const weekPlan = weekSlice(plan, today);

  if (loadingPlan) {
    return (
      <AppShell>
        <div className="grid min-h-[65vh] place-items-center">
          <div className="panel flex items-center gap-4 p-5 font-semibold">
            <Loader2 className="h-5 w-5 animate-spin text-fern" /> Opening selected plan dashboard...
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <section className="overflow-hidden rounded-lg bg-ink text-white shadow-panel">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_auto] lg:items-start lg:p-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/60">Today's topic</p>
            <h1 className="mt-3 text-4xl font-black leading-tight">{topic}</h1>
            <p className="mt-3 text-lg text-white/70">{subtopic} - {todaysHours}h scheduled</p>
            <blockquote className="mt-5 rounded-lg border border-white/10 bg-white/10 p-4">
              <div className="flex gap-3">
                <Sparkles className="mt-1 h-6 w-6 shrink-0 text-amber" />
                <p className="text-xl font-black leading-7">{quote}</p>
              </div>
            </blockquote>
            <div className="mt-5 flex flex-wrap gap-3">
              <Metric label="Today" value={`${todaysHours}h`} />
              <Metric label="Plan days" value={plan.length || 0} />
              <Metric label="Streak" value={`${progress?.streak_days ?? 0}d`} icon={Flame} />
              <Metric label="Exam" value={`${daysRemaining}d`} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2 lg:max-w-[420px] lg:justify-end">
            <Link href={`/quiz?fresh=${Date.now()}`} className="dashboard-action-primary">
              Start quiz <ArrowRight className="h-4 w-4" />
            </Link>
            {studentId ? (
              <a href={`${API_URL}/api/export/studyplan/${studentId}${activePlanId ? `?plan_id=${activePlanId}` : ""}`} className="dashboard-action-secondary">
                <Download className="h-4 w-4" /> Download plan
              </a>
            ) : null}
            <Link href="/plans" className="dashboard-action-secondary">
              Change plan
            </Link>
            <Link href="/setup?new=1" className="dashboard-action-secondary">
              <Plus className="h-4 w-4" /> Add new plan
            </Link>
          </div>
        </div>
      </section>

      <section className="mt-6 grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="panel overflow-hidden">
          <div className="border-b border-ink/10 bg-[#f8faf9] p-5 dark:border-white/10 dark:bg-white/5">
            <p className="section-kicker">Daily lane</p>
            <h2 className="mt-1 text-2xl font-black">Finish concepts, practice, and 3 quizzes</h2>
          </div>
          <div className="grid gap-4 p-5">
            <DailySection icon={BookOpenCheck} title="Important concepts" links={conceptLinks} fallbackUrl={`https://www.google.com/search?q=${encodeURIComponent(`${topic} ${subtopic} important concepts`)}`}>
              {focusPoints.slice(0, 4).map((point) => (
                <p key={point} className="flex gap-2 text-sm leading-6 text-ink/70 dark:text-white/70">
                  <Target className="mt-1 h-4 w-4 shrink-0 text-fern" /> {point}
                </p>
              ))}
              <button type="button" onClick={() => markTask("concepts")} className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md bg-ink px-3 py-2 text-sm font-black text-white hover:bg-fern">
                {dailyTask?.concepts_completed ? <RotateCcw className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                {dailyTask?.concepts_completed ? "Undo concept completion" : "Mark concepts done"}
              </button>
            </DailySection>

            <DailySection icon={PlayCircle} title="Concept videos" links={videoLinks} fallbackUrl={`https://www.youtube.com/results?search_query=${encodeURIComponent(`${topic} ${subtopic} tutorial`)}`} />

            <DailySection icon={ClipboardList} title="Important practice problems" links={practiceLinks} fallbackUrl={`https://www.google.com/search?q=${encodeURIComponent(`${topic} ${subtopic} practice problems`)}`}>
              <button type="button" onClick={() => markTask("practice")} className="focus-ring mt-2 inline-flex items-center gap-2 rounded-md bg-ink px-3 py-2 text-sm font-black text-white hover:bg-fern">
                {dailyTask?.practice_completed ? <RotateCcw className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                {dailyTask?.practice_completed ? "Undo practice completion" : "Mark practice done"}
              </button>
            </DailySection>

            <article className="overflow-hidden rounded-lg border border-fern/20 bg-gradient-to-br from-[#f8faf9] to-white p-0 dark:border-emerald-200/15 dark:from-[#101923] dark:to-[#151f2a]">
              <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_260px] lg:items-center">
                <div>
                  <p className="section-kicker">Quiz mission</p>
                  <h3 className="mt-1 text-2xl font-black">Complete 3 fresh Groq quizzes</h3>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/62 dark:text-white/62">
                    Each quiz should be generated from today's topic, syllabus notes, and your current plan. Finish all three after concepts and practice to close the day.
                  </p>
                  <div className="mt-5 grid gap-2 sm:grid-cols-5">
                    <Step done={!!dailyTask?.concepts_completed} label="Concepts" />
                    <Step done={!!dailyTask?.practice_completed} label="Practice" />
                    {[1, 2, 3].map((count) => <Step key={count} done={(dailyTask?.quiz_count ?? 0) >= count} label={`Quiz ${count}`} />)}
                  </div>
                </div>
                <div className="rounded-lg border border-ink/10 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-white/5">
                  <div className="flex items-end justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.16em] text-ink/45 dark:text-white/45">Mission progress</p>
                      <p className="mt-1 text-4xl font-black text-fern">{completionPercent}%</p>
                    </div>
                    <p className="text-right text-sm font-bold text-ink/55 dark:text-white/55">{Math.min(dailyTask?.quiz_count ?? 0, 3)}/3 quizzes</p>
                  </div>
                  <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-ink/10 dark:bg-white/10">
                    <div className="h-full rounded-full bg-fern transition-all" style={{ width: `${completionPercent}%` }} />
                  </div>
                  <Link href={`/quiz?fresh=${Date.now()}`} className="focus-ring mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-fern px-3 text-sm font-bold text-white hover:bg-emerald-700">
                    <PenSquare className="h-4 w-4" /> Open quiz
                  </Link>
                  <p className="mt-3 text-xs font-semibold text-ink/50 dark:text-white/50">{dailyTask?.day_completed ? "Day complete. Streak counted." : "Finish all five checks for the streak."}</p>
                </div>
              </div>
            </article>
          </div>
        </div>

        <section className="panel p-5">
          <ProgressRing value={coverage} label="Plan done" />
          <div className="mt-6 grid gap-3">
            <Stat icon={ClipboardList} label="Questions" value={progress?.total_questions_attempted ?? 0} loading={loadingProgress && !progress} />
            <Stat icon={Target} label="Accuracy" value={`${progress?.overall_accuracy ?? 0}%`} loading={loadingProgress && !progress} />
            <Stat icon={CheckCircle2} label="Streak" value={`${progress?.streak_days ?? 0} days`} loading={loadingProgress && !progress} />
            <Stat icon={CalendarClock} label="Exam" value={`${daysRemaining} days`} />
          </div>
          {studentId ? (
            <div className="mt-5 grid gap-2">
              <a href={`${API_URL}/api/export/studyplan/${studentId}${activePlanId ? `?plan_id=${activePlanId}` : ""}`} className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/10 px-3 py-2 text-sm font-bold hover:text-fern dark:border-white/10">
                <Download className="h-4 w-4 text-fern" /> Complete day-by-day plan
              </a>
              <a href={`${API_URL}/api/export/flashcards/${studentId}${activePlanId ? `?plan_id=${activePlanId}` : ""}`} className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/10 px-3 py-2 text-sm font-bold hover:text-fern dark:border-white/10">
                <Download className="h-4 w-4 text-fern" /> Flashcards CSV
              </a>
            </div>
          ) : null}
          <RevisionStatsCard revision={revision} history={revisionHistory} completionPercent={completionPercent} loading={loadingRevision && !revision} />
        </section>
      </section>

      <section className="panel mt-6 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="section-kicker">Week plan</p>
            <h2 className="text-xl font-black">Today is highlighted</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/chat" className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-3 text-sm font-black text-white hover:bg-skydeep">
              <MessageSquareText className="h-4 w-4" /> Any problem? Discuss in chat
            </Link>
            <Link href="/revision" className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-4 py-3 text-sm font-black text-white hover:bg-emerald-700">
              <Repeat2 className="h-4 w-4" /> Go for revision plan
            </Link>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-7">
          {weekPlan.map((day) => <WeekCard key={`${day.day}-${day.date}`} day={day} active={day.date === today} />)}
        </div>
      </section>
    </AppShell>
  );
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function weekSlice(plan: StudyDay[], today: string) {
  if (!plan.length) return [];
  const index = Math.max(0, plan.findIndex((day) => day.date === today));
  const start = Math.max(0, index === -1 ? 0 : index);
  return plan.slice(start, start + 7);
}

function DailySection({ icon: Icon, title, links, fallbackUrl, children }: { icon: LucideIcon; title: string; links: StudyResource[]; fallbackUrl: string; children?: React.ReactNode }) {
  const shownLinks = links.length ? links.slice(0, 3) : [{ title, url: fallbackUrl, type: "Search" }];
  return (
    <article className="rounded-lg border border-ink/10 bg-white p-4 dark:border-white/10 dark:bg-[#101923]">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-black">{title}</h3>
          <div className="mt-3 grid gap-2">{children}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {shownLinks.map((resource) => (
              <a key={resource.url} href={resource.url} target="_blank" rel="noreferrer" className="focus-ring inline-flex items-center gap-1 rounded-md bg-mist px-2.5 py-1.5 text-xs font-bold text-fern dark:bg-white/10">
                {resource.title}
                <ExternalLink className="h-3 w-3" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function Step({ done, label }: { done: boolean; label: string }) {
  return (
    <div className={`flex min-h-12 items-center justify-center gap-2 rounded-md border px-2 py-2 text-center text-xs font-black ${done ? "border-fern bg-fern text-white" : "border-ink/10 bg-white text-ink/50 dark:border-white/10 dark:bg-white/5 dark:text-white/45"}`}>
      {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
      {label}
    </div>
  );
}

function WeekCard({ day, active }: { day: StudyDay; active: boolean }) {
  const session: StudySession | undefined = day.sessions[0];
  return (
    <article className={`rounded-lg border p-4 ${active ? "border-fern bg-fern/10 shadow-soft dark:bg-emerald-200/10" : "border-ink/10 bg-[#f8faf9] dark:border-white/10 dark:bg-white/5"}`}>
      <p className="text-xs font-black uppercase tracking-[0.14em] text-fern">Day {day.day}</p>
      <h3 className="mt-2 font-black">{day.date}</h3>
      <p className="mt-3 line-clamp-2 text-sm font-bold text-ink/70 dark:text-white/70">{session?.topic || "Study session"}</p>
      <p className="mt-1 line-clamp-2 text-xs text-ink/55 dark:text-white/55">{session?.subtopic || ""}</p>
    </article>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: string | number; icon?: LucideIcon }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/10 px-4 py-3">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/50">{Icon ? <Icon className="h-4 w-4 text-amber" /> : null}{label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}

function Stat({ icon: Icon, label, value, loading = false }: { icon: LucideIcon; label: string; value: string | number; loading?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-ink/10 bg-[#f8faf9] px-3 py-3 dark:border-white/10 dark:bg-white/10">
      <span className="flex items-center gap-2 text-sm font-medium text-ink/60 dark:text-white/60"><Icon className="h-4 w-4 text-fern" />{label}</span>
      <span className="font-bold">{loading ? <Loader2 className="h-4 w-4 animate-spin text-fern" /> : value}</span>
    </div>
  );
}

function RevisionStatsCard({ revision, history, completionPercent, loading }: { revision: RevisionResponse | null; history: RevisionQuizHistoryItem[]; completionPercent: number; loading: boolean }) {
  const latest = history[0];
  return (
    <div className="mt-5 rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-white/5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200">
          <Brain className="h-5 w-5" />
        </span>
        <div>
          <p className="section-kicker">Revision stats</p>
          <h3 className="mt-1 font-black">Today and quiz health</h3>
        </div>
      </div>
      {loading ? (
        <div className="mt-4 flex items-center gap-2 text-sm font-bold text-ink/55 dark:text-white/55"><Loader2 className="h-4 w-4 animate-spin text-fern" /> Loading revision stats...</div>
      ) : (
        <div className="mt-4 grid gap-3">
          <Stat icon={Repeat2} label="Today lane" value={`${completionPercent}%`} />
          <Stat icon={Brain} label="Revision status" value={revision?.is_first_day ? "First day" : latest ? "Quiz saved" : "Not started"} />
          <Stat icon={BarChart3} label="Latest revision quiz" value={latest ? `${latest.score}%` : "Not taken"} />
          <Stat icon={ClipboardList} label="Revision history" value={history.length} />
          <div className="rounded-md border border-ink/10 bg-white p-3 text-xs font-semibold leading-5 text-ink/60 dark:border-white/10 dark:bg-[#101923] dark:text-white/60">
            {latest?.mistakes.length
              ? `${latest.mistakes.length} revision mistake${latest.mistakes.length === 1 ? "" : "s"} saved with specific feedback.`
              : revision?.message || "Revision stats count only revision quiz submissions from the Revision section."}
          </div>
        </div>
      )}
    </div>
  );
}
