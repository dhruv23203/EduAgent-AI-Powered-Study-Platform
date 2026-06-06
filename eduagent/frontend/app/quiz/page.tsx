"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { QuizCard } from "@/components/QuizCard";
import { currentUserFromStorage, generateQuiz, getDailyTask, getProgress, QuizQuestion, submitQuiz } from "@/lib/api";

export default function QuizPage() {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<Record<string, "A" | "B" | "C" | "D">>({});
  const [locked, setLocked] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const user = currentUserFromStorage();
    if (!user) return;
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    setLoading(true);
    setError("");
    Promise.all([getDailyTask(user.id, new Date().toISOString().slice(0, 10), planId).catch(() => null), getProgress(user.id).catch(() => null)])
      .then(([task, progress]) => {
        const topic = task?.topic || progress?.topics_remaining?.[0] || progress?.weak_areas?.[0] || "Trees and Binary Search Trees";
        const subtopic = task?.subtopic || topic;
        return generateQuiz(user.id, topic, subtopic, "Medium", planId);
      })
      .then((rows) => { setQuestions(rows); setIndex(0); setSelected({}); setLocked(false); setSummary(null); })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Quiz generation failed."))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const question = questions[index];
  async function finish() {
    const user = currentUserFromStorage();
    if (!user) return;
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    const result = await submitQuiz(user.id, questions.map((item) => ({ question_id: item.id, selected_option: selected[item.id] || "A" })), planId);
    setSummary(result);
  }

  if (loading) return <AppShell><div className="panel flex items-center gap-4 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Generating fresh Groq quiz...</div></AppShell>;
  return (
    <AppShell>
      {error ? <div className="panel border-coral/25 p-5 text-coral">{error}</div> : null}
      {summary ? <section className="mx-auto max-w-xl rounded-lg bg-ink p-8 text-center text-white shadow-panel"><p className="section-kicker">Quiz complete</p><h1 className="mt-2 text-6xl font-black">{summary.score}%</h1><p className="mt-3 text-xl">{summary.correct} correct, {summary.wrong} to revise.</p><div className="mt-6 grid grid-cols-2 gap-3"><div className="rounded-lg bg-white/10 p-4"><span>Coins</span><b className="block text-2xl">+{summary.rewards?.coins_earned ?? 0}</b></div><div className="rounded-lg bg-white/10 p-4"><span>Badges</span><b className="block text-2xl">{summary.rewards?.new_badges?.length ?? 0}</b></div></div><Link href="/progress" className="focus-ring mt-6 inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-emerald-700">View weak areas <ArrowRight className="h-4 w-4" /></Link></section> : question ? <><div className="mb-5 rounded-lg bg-white p-4 shadow-soft dark:bg-white/10"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">Fresh quiz</p><h1 className="mt-1 text-2xl font-black">{question.topic}</h1></div><button onClick={() => setRefreshKey((v) => v + 1)} className="focus-ring inline-flex items-center gap-2 rounded-md bg-fern px-3 py-2 text-sm font-black text-white hover:bg-emerald-700"><RefreshCw className="h-4 w-4" /> New Groq quiz</button></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-mist dark:bg-white/10"><div className="h-full bg-fern" style={{ width: `${((index + 1) / questions.length) * 100}%` }} /></div></div><div className="mx-auto max-w-3xl"><QuizCard question={question} selected={selected[question.id]} locked={locked} onSelect={(option) => setSelected((current) => ({ ...current, [question.id]: option }))} /><div className="mt-5 flex justify-between"><button disabled={index === 0} onClick={() => { setIndex((v) => Math.max(0, v - 1)); setLocked(false); }} className="focus-ring inline-flex items-center gap-2 rounded-lg border border-ink/10 bg-white px-4 py-3 font-semibold disabled:opacity-50 dark:border-white/10 dark:bg-white/10"><ArrowLeft className="h-4 w-4" /> Previous</button>{locked ? index === questions.length - 1 ? <button onClick={finish} className="focus-ring rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep">Finish quiz</button> : <button onClick={() => { setIndex((v) => v + 1); setLocked(false); }} className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep">Next <ArrowRight className="h-4 w-4" /></button> : <button disabled={!selected[question.id]} onClick={() => setLocked(true)} className="focus-ring rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep disabled:opacity-50">Check answer</button>}</div></div></> : null}
    </AppShell>
  );
}
