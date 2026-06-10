"use client";

import { useEffect, useState } from "react";
import { Brain, ClipboardList, Loader2, PartyPopper, Repeat2, Target, type LucideIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StudyPlanView } from "@/components/StudyPlanView";
import { getRevision, RevisionResponse, studentIdFromStorage } from "@/lib/api";

export default function RevisionPage() {
  const [data, setData] = useState<RevisionResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null; getRevision(studentIdFromStorage(), planId).then(setData).catch((e) => setError(e instanceof Error ? e.message : "Revision unavailable.")); }, []);
  return (
    <AppShell>
      <section className="overflow-hidden rounded-lg bg-ink text-white shadow-panel">
        <div className="grid gap-5 p-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="section-kicker">Revision</p>
            <h1 className="mt-2 text-3xl font-black">Today's focused revision</h1>
            <p className="mt-2 max-w-2xl text-white/68">Only previous quizzes and completed concepts are used. Future plan topics stay out of this section.</p>
          </div>
          {data && !data.is_first_day ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <MiniStat icon={Repeat2} label="Revision need" value={`${data.revision_percentage}%`} />
              <MiniStat icon={Target} label="Quiz accuracy" value={`${data.quiz_accuracy}%`} />
              <MiniStat icon={ClipboardList} label="Self-check" value={data.total_revision_questions} />
            </div>
          ) : null}
        </div>
      </section>
      {error ? <div className="panel mt-6 border-coral/20 p-5 text-coral">{error}</div> : null}
      {!data && !error ? <div className="panel mt-6 flex items-center gap-3 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Loading revision...</div> : null}
      {data?.is_first_day ? (
        <section className="panel mt-6 p-6 text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200"><PartyPopper className="h-7 w-7" /></span>
          <h2 className="mt-4 text-2xl font-black">Nothing to revise today</h2>
          <p className="mx-auto mt-2 max-w-xl leading-7 text-ink/65 dark:text-white/65">{data.message}</p>
        </section>
      ) : null}
      {data && !data.is_first_day ? (
        <>
          <section className="panel mt-6 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="section-kicker">Priority</p>
                <h2 className="text-xl font-black">What to fix first</h2>
                <p className="mt-1 text-sm text-ink/55 dark:text-white/55">{data.message}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">{data.priority_topics.map((topic) => <span key={topic} className="rounded-md bg-fern/10 px-3 py-2 font-black text-fern dark:bg-emerald-300/10 dark:text-emerald-200">{topic}</span>)}</div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {data.exam_focus.map((item) => <div key={item} className="rounded-lg border border-ink/10 bg-[#f8faf9] p-3 text-sm font-bold text-ink/70 dark:border-white/10 dark:bg-white/5 dark:text-white/70">{item}</div>)}
            </div>
          </section>
          <div className="mt-6"><StudyPlanView plan={data.revision_plan} /></div>
          <section className="panel mt-6 p-5">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200"><Brain className="h-5 w-5" /></span>
              <div>
                <p className="section-kicker">Revision quiz</p>
                <h2 className="text-xl font-black">10 specific self-check questions</h2>
              </div>
            </div>
            <ol className="mt-5 grid gap-3 lg:grid-cols-2">
              {data.quiz_questions.map((question, index) => (
                <li key={`${question}-${index}`} className="flex gap-3 rounded-lg border border-ink/10 bg-[#f8faf9] p-4 text-sm leading-6 text-ink/72 dark:border-white/10 dark:bg-[#101923] dark:text-white/72">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-fern text-xs font-black text-white">{index + 1}</span>
                  {question}
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}

function MiniStat({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-right">
      <p className="flex items-center justify-end gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-white/50"><Icon className="h-4 w-4 text-amber" /> {label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}
