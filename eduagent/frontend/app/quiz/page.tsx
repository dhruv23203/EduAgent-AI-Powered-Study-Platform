"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowRight, Award, Bot, Coins, KeyRound, Loader2, RefreshCw, Trophy, WifiOff } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { QuizCard } from "@/components/QuizCard";
import { currentUserFromStorage, generateQuiz, getDailyTask, getProgress, QuizQuestion, submitQuiz } from "@/lib/api";

type QuizUnavailableKind = "cooling" | "no-key" | "offline" | "bad-output";

function classifyQuizUnavailable(error: string): QuizUnavailableKind | null {
  const text = error.toLowerCase();
  if (!text) return null;
  if (text.includes("rate-limited") || text.includes("rate limit") || text.includes("cooling") || text.includes("temporarily unavailable") || text.includes("all configured")) return "cooling";
  if (text.includes("not reachable") || text.includes("failed to fetch")) return "offline";
  if (text.includes("key is not configured") || text.includes("no configured")) return "no-key";
  if (text.includes("malformed json") || text.includes("did not return quiz questions") || text.includes("did not return enough")) return "bad-output";
  return null;
}

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
    setQuestions([]);
    setIndex(0);
    setSelected({});
    setLocked(false);
    setSummary(null);
    Promise.all([getDailyTask(user.id, new Date().toISOString().slice(0, 10), planId).catch(() => null), getProgress(user.id, planId).catch(() => null)])
      .then(([task, progress]) => {
        const topic = task?.topic || progress?.topics_remaining?.[0] || progress?.weak_areas?.[0] || "Trees and Binary Search Trees";
        const subtopic = task?.subtopic || topic;
        return generateQuiz(user.id, topic, subtopic, "Medium", planId);
      })
      .then((rows) => {
        if (!rows.length) throw new Error("Quiz service returned no questions. Please retry.");
        setQuestions(rows); setIndex(0); setSelected({}); setLocked(false); setSummary(null);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Quiz generation failed."))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const question = questions[index];
  async function finish() {
    const user = currentUserFromStorage();
    if (!user) return;
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    setError("");
    try {
      const result = await submitQuiz(user.id, questions.map((item) => ({ question_id: item.id, selected_option: selected[item.id] || "A" })), planId);
      setSummary(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Quiz submission failed. Generate a fresh quiz and try again.");
    }
  }

  function startNewQuiz() {
    setSummary(null);
    setQuestions([]);
    setSelected({});
    setLocked(false);
    setIndex(0);
    setRefreshKey((value) => value + 1);
  }

  if (loading) return <AppShell><div className="panel flex items-center gap-4 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Generating a fresh topic-matched quiz...</div></AppShell>;
  const unavailableKind = !summary && !question ? (classifyQuizUnavailable(error) || "bad-output") : null;
  if (unavailableKind) return <AppShell><QuizUnavailableScreen kind={unavailableKind} onRetry={startNewQuiz} /></AppShell>;
  return (
    <AppShell>
      {error ? <div className="panel border-coral/25 p-5 text-coral">{error}</div> : null}
      {summary ? <section className="mx-auto max-w-2xl overflow-hidden rounded-lg border border-ink/10 bg-white text-center shadow-panel dark:border-white/10 dark:bg-[#151f2a]"><div className="bg-ink px-8 py-7 text-white"><span className="mx-auto grid h-14 w-14 place-items-center rounded-lg bg-fern"><Trophy className="h-7 w-7" /></span><p className="section-kicker mt-5">Quiz complete</p><h1 className="mt-2 text-6xl font-black">{summary.score}%</h1><p className="mt-3 text-xl text-white/78">{summary.correct} correct, {summary.wrong} to revise.</p></div><div className="grid gap-3 p-6 sm:grid-cols-2"><div className="rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-white/5"><Coins className="mx-auto h-5 w-5 text-fern" /><span className="mt-2 block text-sm font-bold text-ink/55 dark:text-white/55">Plan coins earned</span><b className="block text-3xl font-black text-fern">+{summary.rewards?.coins_earned ?? 0}</b></div><div className="rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-white/5"><Award className="mx-auto h-5 w-5 text-fern" /><span className="mt-2 block text-sm font-bold text-ink/55 dark:text-white/55">New badges</span><b className="block text-3xl font-black text-fern">{summary.rewards?.new_badges?.length ?? 0}</b></div></div><div className="flex flex-wrap justify-center gap-3 border-t border-ink/10 p-6 dark:border-white/10"><button type="button" onClick={startNewQuiz} className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-emerald-700"><RefreshCw className="h-4 w-4" /> Start new Groq quiz</button><Link href="/progress" className="focus-ring inline-flex items-center gap-2 rounded-lg border border-ink/10 px-5 py-3 font-bold text-ink hover:text-fern dark:border-white/10 dark:text-white">View weak areas <ArrowRight className="h-4 w-4" /></Link></div></section> : question ? <><div className="mb-5 rounded-lg bg-white p-4 shadow-soft dark:bg-white/10"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">Fresh Groq daily quiz</p><h1 className="mt-1 text-2xl font-black">{question.topic}</h1></div><button onClick={() => setRefreshKey((v) => v + 1)} className="focus-ring inline-flex items-center gap-2 rounded-md bg-fern px-3 py-2 text-sm font-black text-white hover:bg-emerald-700"><RefreshCw className="h-4 w-4" /> New Groq quiz</button></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-mist dark:bg-white/10"><div className="h-full bg-fern" style={{ width: `${((index + 1) / questions.length) * 100}%` }} /></div></div><div className="mx-auto max-w-3xl"><QuizCard question={question} selected={selected[question.id]} locked={locked} onSelect={(option) => setSelected((current) => ({ ...current, [question.id]: option }))} /><div className="mt-5 flex justify-between"><button disabled={index === 0} onClick={() => { setIndex((v) => Math.max(0, v - 1)); setLocked(false); }} className="focus-ring inline-flex items-center gap-2 rounded-lg border border-ink/10 bg-white px-4 py-3 font-semibold disabled:opacity-50 dark:border-white/10 dark:bg-white/10"><ArrowLeft className="h-4 w-4" /> Previous</button>{locked ? index === questions.length - 1 ? <button onClick={finish} className="focus-ring rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep">Finish quiz</button> : <button onClick={() => { setIndex((v) => v + 1); setLocked(false); }} className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep">Next <ArrowRight className="h-4 w-4" /></button> : <button disabled={!selected[question.id]} onClick={() => setLocked(true)} className="focus-ring rounded-lg bg-fern px-5 py-3 font-bold text-white hover:bg-skydeep disabled:opacity-50">Check answer</button>}</div></div></> : null}
    </AppShell>
  );
}

function QuizUnavailableScreen({ kind, onRetry }: { kind: QuizUnavailableKind; onRetry: () => void }) {
  const copy = {
    cooling: {
      icon: AlertTriangle,
      eyebrow: "Groq unavailable",
      title: "Quiz AI is cooling down",
      body: "All configured Groq keys are temporarily unavailable or rate-limited. Wait a little, then retry generation.",
      detail: "Your saved study plan is fine. Only new Groq quiz generation is paused right now.",
    },
    "no-key": {
      icon: KeyRound,
      eyebrow: "Key missing",
      title: "Groq key is not available",
      body: "Add a valid Groq API key in the backend environment file, then restart the backend server.",
      detail: "EduAgent is set to Groq-only quizzes, so it will not show hardcoded fallback questions.",
    },
    offline: {
      icon: WifiOff,
      eyebrow: "Backend offline",
      title: "Quiz service is not reachable",
      body: "The frontend cannot reach the FastAPI backend. Start the backend and keep it running.",
      detail: "Expected backend URL: http://127.0.0.1:8000",
    },
    "bad-output": {
      icon: Bot,
      eyebrow: "Try again",
      title: "Groq returned an incomplete quiz",
      body: "The model responded, but the quiz format was not usable. Generate again for a fresh response.",
      detail: "EduAgent will keep quizzes Groq-generated and concept-focused.",
    },
  }[kind];
  const Icon = copy.icon;
  return (
    <section className="mx-auto grid min-h-[calc(100vh-8rem)] max-w-4xl place-items-center px-2">
      <div className="w-full overflow-hidden rounded-lg border border-coral/20 bg-white text-center shadow-panel dark:border-coral/25 dark:bg-[#151f2a]">
        <div className="bg-[#fff7f6] px-6 py-8 dark:bg-coral/10">
          <span className="mx-auto grid h-16 w-16 place-items-center rounded-lg bg-coral text-white shadow-soft">
            <Icon className="h-8 w-8" />
          </span>
          <p className="mt-5 text-sm font-semibold uppercase tracking-[0.18em] text-coral">{copy.eyebrow}</p>
          <h1 className="mt-2 text-3xl font-black text-ink dark:text-white">{copy.title}</h1>
          <p className="mx-auto mt-3 max-w-xl text-base leading-7 text-ink/65 dark:text-white/65">{copy.body}</p>
        </div>
        <div className="px-6 py-6">
          <div className="mx-auto max-w-xl rounded-md border border-ink/10 bg-[#f8faf9] px-4 py-3 text-sm font-semibold text-ink/65 dark:border-white/10 dark:bg-white/5 dark:text-white/65">{copy.detail}</div>
          <button type="button" onClick={onRetry} className="focus-ring mt-5 inline-flex items-center gap-2 rounded-lg bg-fern px-5 py-3 font-black text-white hover:bg-emerald-700">
            <RefreshCw className="h-4 w-4" /> Retry Groq quiz
          </button>
        </div>
      </div>
    </section>
  );
}
