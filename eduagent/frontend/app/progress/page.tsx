"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Award, BadgeCheck, Coins, ExternalLink, Flame, Loader2, RotateCcw, Target } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { WeaknessChart } from "@/components/WeaknessChart";
import { getProgress, ProgressResponse, recoverStreak, studentIdFromStorage } from "@/lib/api";

export default function ProgressPage() {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  function load() { const id = studentIdFromStorage(); const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null; const cacheKey = `eduagent_progress_${id}_${planId || "all"}`; const cached = localStorage.getItem(cacheKey); if (cached) setProgress(JSON.parse(cached)); setLoading(true); getProgress(id, planId).then((p) => { setProgress(p); localStorage.setItem(cacheKey, JSON.stringify(p)); setError(""); }).catch((e) => setError(e instanceof Error ? e.message : "Progress will appear after your first quiz.")).finally(() => setLoading(false)); }
  useEffect(load, []);
  async function recover() { await recoverStreak(studentIdFromStorage()); load(); }
  return (
    <AppShell>
      <section className="rounded-lg bg-white p-6 shadow-soft dark:bg-white/10"><p className="section-kicker">Progress</p><div className="mt-2 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-black">Performance cockpit</h1><p className="mt-2 max-w-2xl text-ink/65 dark:text-white/65">Accuracy, mistakes, streaks, coins, badges, and next-step feedback in one view.</p></div>{progress ? <div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric icon={Target} label="Accuracy" value={`${progress.overall_accuracy}%`} /><Metric icon={Flame} label="Streak" value={`${progress.streak_days}d`} /><Metric icon={Coins} label="Coins" value={progress.rewards?.coins ?? 0} /><Metric icon={Award} label="Badges" value={progress.rewards?.badges.length ?? 0} /></div> : null}</div></section>
      {loading && !progress ? <div className="panel mt-6 flex items-center gap-3 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Loading progress...</div> : null}
      {error ? <div className="panel mt-6 border-coral/20 p-5 text-coral">{error}</div> : null}
      {progress ? <><section className="panel mt-6 p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="section-kicker">Daily Heatmap</p><h2 className="mt-1 text-xl font-black">LeetCode-style consistency grid</h2><p className="mt-1 text-sm text-ink/55 dark:text-white/55">{progress.heatmap[0]?.date} to {progress.heatmap.at(-1)?.date}</p></div><button onClick={recover} className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-3 text-sm font-bold text-white hover:bg-skydeep"><RotateCcw className="h-4 w-4" /> Recover streak ({progress.rewards?.recover_streak_cost ?? 75} coins)</button></div><Heatmap days={progress.heatmap} /></section><BadgeTargets progress={progress} /><div className="mt-6"><WeaknessChart data={progress.accuracy_by_topic} /></div><section className="panel mt-6 p-5"><p className="section-kicker">Mistake Patterns</p><h2 className="text-xl font-black">Topic-specific wrong-answer review</h2>{progress.mistakes.length ? <div className="mt-5 grid gap-4 lg:grid-cols-2">{progress.mistakes.map((item) => <article key={`${item.topic}-${item.subtopic}`} className="rounded-lg border border-coral/20 bg-coral/5 p-4 dark:bg-coral/10"><div className="flex items-start gap-3"><AlertCircle className="mt-1 h-5 w-5 shrink-0 text-coral" /><div><h3 className="font-black">{item.topic}</h3><p className="mt-1 text-sm font-semibold text-ink/60 dark:text-white/60">{item.subtopic || "General"} | {item.mistakes} miss(es)</p></div></div><p className="mt-3 text-sm leading-6 text-ink/70 dark:text-white/70">{item.feedback}</p><div className="mt-3 rounded-md bg-white p-3 text-sm dark:bg-[#101923]"><p className="font-bold">Latest missed question</p><p className="mt-1 text-ink/65 dark:text-white/65">{item.last_question}</p><p className="mt-2 text-xs font-black uppercase tracking-[0.14em] text-ink/45 dark:text-white/45">Selected {item.selected_answer} | Correct {item.correct_answer}</p></div><div className="mt-3 flex flex-wrap gap-2">{item.resources.slice(0, 2).map((resource) => <a key={resource.url} href={resource.url} target="_blank" rel="noreferrer" className="focus-ring inline-flex items-center gap-1 rounded-md bg-white px-2.5 py-1.5 text-xs font-bold text-fern dark:bg-white/10">{resource.title}<ExternalLink className="h-3 w-3" /></a>)}</div></article>)}</div> : <p className="mt-3 text-sm text-ink/60 dark:text-white/60">No wrong-answer pattern yet. Take a quiz and EduAgent will diagnose mistakes here.</p>}</section><section className="panel mt-6 p-5"><p className="section-kicker">Feedback Loop</p><h2 className="text-xl font-black">Groq-targeted improvement plan</h2><p className="mt-3 leading-7 text-ink/70 dark:text-white/65">{progress.insight}</p><div className="mt-5 grid gap-4 lg:grid-cols-2">{progress.feedback.map((item) => <article key={item.topic} className="rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-[#101923]"><div className="flex items-start justify-between gap-3"><h3 className="font-black">{item.topic}</h3><span className={`rounded-md px-2 py-1 text-xs font-black ${item.priority === "High" ? "bg-coral/10 text-coral" : item.priority === "Medium" ? "bg-amber/20 text-ink dark:text-amber" : "bg-fern/10 text-fern"}`}>{item.priority}</span></div><p className="mt-1 text-sm text-ink/60 dark:text-white/60">{item.diagnosis}</p><ol className="mt-3 grid gap-2 text-sm">{item.next_steps.map((step, i) => <li key={step} className="flex gap-2"><span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-fern text-xs font-bold text-white">{i + 1}</span>{step}</li>)}</ol></article>)}</div></section></> : null}
    </AppShell>
  );
}

function Metric({ icon: Icon, label, value }: any) { return <div className="rounded-lg bg-mist px-4 py-3 text-right dark:bg-white/10"><p className="flex items-center justify-end gap-1 text-sm font-semibold text-ink/60 dark:text-white/55"><Icon className="h-4 w-4 text-fern" />{label}</p><p className="mt-1 text-2xl font-black text-fern">{value}</p></div>; }
function Heatmap({ days }: { days: ProgressResponse["heatmap"] }) {
  const weeks = buildWeeks(days);
  return (
    <div className="mt-5 overflow-x-auto pb-2">
      <div className="inline-grid grid-cols-[32px_auto] gap-2">
        <div className="grid grid-rows-7 gap-1 pt-0 text-[10px] font-bold text-ink/45 dark:text-white/45">
          {["", "Mon", "", "Wed", "", "Fri", ""].map((label, index) => <span key={`${label}-${index}`} className="h-4 leading-4">{label}</span>)}
        </div>
        <div className="flex gap-1">
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="grid grid-rows-7 gap-1">
              {week.map((day, dayIndex) => <span key={day?.date || `${weekIndex}-${dayIndex}`} title={day ? `${day.date}: ${day.count}/5 missions, ${day.accuracy}% accuracy` : ""} className={`h-4 w-4 rounded-[3px] border ${heatClass(day)}`} />)}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs font-bold text-ink/50 dark:text-white/50">
        <span>Less</span>
        {[0, 1, 2, 3, 5].map((count) => <span key={count} className={`h-3.5 w-3.5 rounded-[3px] border ${heatClass({ count, date: "", accuracy: 0, recovered: false })}`} />)}
        <span>More</span>
      </div>
    </div>
  );
}

function buildWeeks(days: ProgressResponse["heatmap"]) {
  const weeks: Array<Array<ProgressResponse["heatmap"][number] | null>> = [];
  days.forEach((day) => {
    const dayIndex = new Date(`${day.date}T00:00:00`).getDay();
    if (!weeks.length || dayIndex === 0) weeks.push(Array(7).fill(null));
    weeks[weeks.length - 1][dayIndex] = day;
  });
  return weeks;
}

function heatClass(day: ProgressResponse["heatmap"][number] | { count: number; recovered: boolean } | null) {
  if (!day) return "border-transparent bg-transparent";
  if (day.recovered || day.count >= 5) return "border-[#216e39] bg-[#216e39]";
  if (day.count >= 4) return "border-[#30a14e] bg-[#30a14e]";
  if (day.count >= 2) return "border-[#40c463] bg-[#40c463]";
  if (day.count >= 1) return "border-[#9be9a8] bg-[#9be9a8]";
  return "border-ink/10 bg-[#ebedf0] dark:border-white/10 dark:bg-white/10";
}
function BadgeTargets({ progress }: { progress: ProgressResponse }) { const badges = new Set(progress.rewards?.badges ?? []); const targets = [["First Quiz", progress.total_questions_attempted, 1], ["Sharp Shooter", progress.overall_accuracy, 80], ["3 Day Flame", progress.streak_days, 3], ["Weekly Warrior", progress.streak_days, 7], ["Coin Collector", progress.rewards?.coins ?? 0, 250]] as const; return <section className="panel mt-6 p-5"><p className="section-kicker">Badges & Targets</p><h2 className="mt-1 text-xl font-black">Earn rewards with clear missions</h2><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{targets.map(([name, current, target]) => { const earned = badges.has(name) || current >= target; return <article key={name} className={`rounded-lg border p-4 ${earned ? "border-fern/30 bg-fern/5" : "border-ink/10 bg-[#f8faf9] dark:border-white/10 dark:bg-white/10"}`}><div className="flex justify-between"><BadgeCheck className={earned ? "text-fern" : "text-ink/40"} /><span className="text-xs font-black">{earned ? "Earned" : "Locked"}</span></div><h3 className="mt-4 font-black">{name}</h3><div className="mt-3 h-2 overflow-hidden rounded-full bg-ink/10 dark:bg-white/10"><div className="h-full rounded-full bg-fern" style={{ width: `${Math.min(100, Math.round((current / target) * 100))}%` }} /></div></article>; })}</div></section>; }
