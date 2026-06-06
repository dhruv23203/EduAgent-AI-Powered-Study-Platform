"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StudyPlanView } from "@/components/StudyPlanView";
import { getRevision, RevisionResponse, studentIdFromStorage } from "@/lib/api";

export default function RevisionPage() {
  const [data, setData] = useState<RevisionResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getRevision(studentIdFromStorage()).then(setData).catch((e) => setError(e instanceof Error ? e.message : "Revision unavailable.")); }, []);
  return (
    <AppShell>
      <section className="rounded-lg bg-white p-6 shadow-soft dark:bg-white/10"><p className="section-kicker">Revision</p><h1 className="mt-2 text-3xl font-black">Today's 30-minute Groq revision</h1><p className="mt-2 max-w-2xl text-ink/65 dark:text-white/65">Revision uses topics and quizzes completed before today, with yesterday's work first. It does not pull future plan topics.</p></section>
      {error ? <div className="panel mt-6 border-coral/20 p-5 text-coral">{error}</div> : null}
      {!data && !error ? <div className="panel mt-6 flex items-center gap-3 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Loading revision...</div> : null}
      {data ? <><section className="panel mt-6 p-5"><p className="section-kicker">Priority</p><h2 className="text-xl font-black">What to fix first</h2><div className="mt-4 flex flex-wrap gap-2">{data.priority_topics.map((topic) => <span key={topic} className="rounded-md bg-fern/10 px-3 py-2 font-black text-fern dark:bg-emerald-300/10 dark:text-emerald-200">{topic}</span>)}</div></section><div className="mt-6"><StudyPlanView plan={data.revision_plan} /></div></> : null}
    </AppShell>
  );
}
