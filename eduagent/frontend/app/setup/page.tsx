"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, CalendarDays, CheckCircle2, GraduationCap, Loader2, UploadCloud } from "lucide-react";
import { currentUserFromStorage, generatePlan, uploadPdf, UserProfile } from "@/lib/api";

export default function SetupPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [syllabus, setSyllabus] = useState<File | null>(null);
  const [notes, setNotes] = useState<File | null>(null);
  const [examDate, setExamDate] = useState("");
  const [dailyHours, setDailyHours] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const profile = currentUserFromStorage();
    if (!profile) {
      router.replace("/login?mode=login");
      return;
    }
    setUser(profile);
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      if (syllabus) await uploadPdf("syllabus", user.id, syllabus);
      if (notes) await uploadPdf("notes", user.id, notes);
      const created = await generatePlan(user.id, examDate, dailyHours, true);
      if (created.id) {
        localStorage.setItem("eduagent_selected_plan_id", String(created.id));
      }
      router.replace("/plans");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not save plan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-ink text-white">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1800&q=80')] bg-cover bg-center opacity-35" />
      <div className="absolute inset-0 bg-ink/90" />
      <div className="hero-grid absolute inset-0" />
      <section className="relative mx-auto max-w-7xl px-6 py-10">
        <header className="flex items-center justify-between gap-4">
          <Link href="/plans" className="focus-ring flex items-center gap-3 rounded-lg text-white"><span className="grid h-12 w-12 place-items-center rounded-lg bg-fern"><GraduationCap /></span><b className="text-2xl">EduAgent</b></Link>
          <Link href="/plans" className="focus-ring inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-4 py-3 text-sm font-bold"><ArrowLeft className="h-4 w-4" /> Back to plans</Link>
        </header>
        <div className="mt-12 max-w-4xl">
          <p className="section-kicker">Secure setup</p>
          <h1 className="mt-3 text-5xl font-black">Create a new saved study plan</h1>
          <p className="mt-4 text-xl leading-8 text-white/75">Upload syllabus, notes, and exam date. EduAgent saves this plan to your account database.</p>
        </div>
        <form onSubmit={submit} className="mt-8 rounded-lg border border-white/20 bg-white/95 p-6 text-ink shadow-panel dark:bg-[#111b26]/95 dark:text-white">
          {error ? <div className="mb-5 rounded-lg border border-coral/25 bg-coral/10 p-3 font-bold text-coral">{error}</div> : null}
          <div className="grid gap-4 lg:grid-cols-2">
            <FileBox label="Syllabus PDF" file={syllabus} onChange={setSyllabus} />
            <FileBox label="Lecture notes PDF" file={notes} onChange={setNotes} />
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
            <label><span className="flex items-center gap-2 font-bold"><CalendarDays className="h-4 w-4 text-fern" /> Exam date</span><input type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)} className="focus-ring mt-2 h-12 w-full rounded-lg border border-ink/10 px-4 dark:border-white/10" required /></label>
            <label><span className="font-bold">Daily hours: {dailyHours}</span><input type="range" min={1} max={12} value={dailyHours} onChange={(e) => setDailyHours(Number(e.target.value))} className="mt-4 w-full accent-fern" /></label>
            <button disabled={loading || !user} className="focus-ring inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-ink px-6 font-black text-white hover:bg-fern disabled:opacity-60 dark:bg-fern dark:hover:bg-skydeep">{loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />} Save new plan</button>
          </div>
        </form>
      </section>
    </main>
  );
}

function FileBox({ label, file, onChange }: { label: string; file: File | null; onChange: (file: File | null) => void }) {
  return (
    <label className="cursor-pointer rounded-lg border border-dashed border-ink/20 bg-[#f8faf9] p-5 shadow-soft transition hover:border-fern dark:border-white/10 dark:bg-white/10">
      <span className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-lg bg-mist text-fern dark:bg-white/10"><UploadCloud /></span><span><b className="block">{label}</b><span className="text-sm text-ink/55 dark:text-white/55">{file ? file.name : "Choose file"}</span></span></span>
      <input type="file" accept=".pdf,.txt,text/plain,application/pdf" className="sr-only" onChange={(event) => onChange(event.target.files?.[0] ?? null)} />
    </label>
  );
}
