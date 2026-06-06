"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CareerMap } from "@/components/CareerMap";
import { CareerResponse, getCareers, studentIdFromStorage } from "@/lib/api";

export default function CareerPage() {
  const [data, setData] = useState<CareerResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getCareers(studentIdFromStorage()).then(setData).catch((e) => setError(e instanceof Error ? e.message : "Career data unavailable.")); }, []);
  return (
    <AppShell>
      <section className="rounded-lg bg-white p-6 shadow-soft dark:bg-white/10"><p className="section-kicker">Career</p><h1 className="mt-2 text-3xl font-black">Career map</h1><p className="mt-2 max-w-2xl text-ink/65 dark:text-white/65">Translate syllabus strengths into role matches, practical skills, and course next steps.</p></section>
      {error ? <div className="panel mt-6 border-coral/20 p-5 text-coral">{error}</div> : null}
      {!data && !error ? <div className="panel mt-6 flex items-center gap-4 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Loading career map...</div> : null}
      {data ? <div className="mt-6"><CareerMap careers={data.careers} /></div> : null}
    </AppShell>
  );
}
